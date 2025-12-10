# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
JVM Thread Dump Parser for Heimr.

Parses jstack output to extract thread states, detect deadlocks,
and identify lock contention patterns.
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ThreadInfo:
    """Represents a single thread from a thread dump."""
    name: str
    state: str  # RUNNABLE, BLOCKED, WAITING, TIMED_WAITING, NEW, TERMINATED
    tid: str = ""
    nid: str = ""
    daemon: bool = False
    priority: int = 0
    stack_trace: List[str] = field(default_factory=list)
    waiting_on: Optional[str] = None  # Lock address if BLOCKED/WAITING
    lock_owner: Optional[str] = None  # Thread holding the lock
    locked_synchronizers: List[str] = field(default_factory=list)


@dataclass 
class DeadlockInfo:
    """Represents a detected deadlock."""
    threads: List[str]
    description: str


class ThreadDumpParser:
    """
    Parses JVM thread dumps (jstack output format).
    
    Example usage:
        parser = ThreadDumpParser(filepath='/path/to/threaddump.txt')
        result = parser.parse()
        print(result['summary'])
    """
    
    # Regex patterns for parsing jstack output
    THREAD_HEADER_PATTERN = re.compile(
        r'^"(?P<name>[^"]+)"'
        r'(?:\s+#\d+)?'  # Optional thread number
        r'(?:\s+daemon)?'  # Optional daemon flag
        r'(?:\s+prio=(?P<prio>\d+))?'  # Optional priority
        r'(?:\s+os_prio=\d+)?'  # Optional OS priority
        r'(?:\s+cpu=[\d.]+[a-z]+)?'  # Optional CPU time
        r'(?:\s+elapsed=[\d.]+[a-z]+)?'  # Optional elapsed
        r'(?:\s+tid=(?P<tid>0x[0-9a-fA-F]+))?'  # Optional TID
        r'(?:\s+nid=(?P<nid>0x[0-9a-fA-F]+|\d+))?'  # Optional NID
        r'(?:\s+(?P<status>[^\[]+))?'  # Status before brackets
        r'(?:\s+\[(?P<address>0x[0-9a-fA-F]+)\])?'  # Optional address
    )
    
    STATE_PATTERN = re.compile(r'java\.lang\.Thread\.State:\s+(\w+)')
    WAITING_ON_PATTERN = re.compile(r'- waiting to lock <(0x[0-9a-fA-F]+)>')
    PARKING_PATTERN = re.compile(r'- parking to wait for\s+<(0x[0-9a-fA-F]+)>')
    LOCKED_PATTERN = re.compile(r'- locked <(0x[0-9a-fA-F]+)>')
    WAITING_ON_MONITOR_PATTERN = re.compile(r'- waiting on <(0x[0-9a-fA-F]+)>')
    LOCK_OWNER_PATTERN = re.compile(r'owned by "([^"]+)"')
    DEADLOCK_PATTERN = re.compile(r'Found (\d+) deadlock')
    
    def __init__(self, filepath: str = None, content: str = None):
        """
        Initialize parser with either a file path or raw content.
        
        Args:
            filepath: Path to thread dump file
            content: Raw thread dump content string
        """
        if filepath:
            with open(filepath, 'r') as f:
                self.content = f.read()
        elif content:
            self.content = content
        else:
            raise ValueError("Either filepath or content must be provided")
        
        self.threads: List[ThreadInfo] = []
        self.deadlocks: List[DeadlockInfo] = []
        self.jvm_info: Dict[str, str] = {}
        
    def parse(self) -> Dict[str, Any]:
        """
        Parse the thread dump and return structured data.
        
        Returns:
            Dictionary containing:
            - threads: List of ThreadInfo objects as dicts
            - summary: Aggregated statistics
            - deadlocks: List of detected deadlocks
            - hot_locks: Locks with multiple waiters
            - jvm_info: JVM version and timestamp info
        """
        lines = self.content.split('\n')
        self._parse_jvm_info(lines)
        self._parse_threads(lines)
        self._detect_deadlocks(lines)
        
        return {
            'threads': [self._thread_to_dict(t) for t in self.threads],
            'summary': self._generate_summary(),
            'deadlocks': [{'threads': d.threads, 'description': d.description} for d in self.deadlocks],
            'hot_locks': self._find_hot_locks(),
            'jvm_info': self.jvm_info
        }
    
    def _parse_jvm_info(self, lines: List[str]) -> None:
        """Extract JVM version and timestamp from dump header."""
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            if 'Full thread dump' in line:
                self.jvm_info['jvm_version'] = line.strip()
            elif line.strip() and i == 0:
                # First line often contains timestamp
                self.jvm_info['timestamp'] = line.strip()
    
    def _parse_threads(self, lines: List[str]) -> None:
        """Parse individual thread entries."""
        current_thread: Optional[ThreadInfo] = None
        in_stack_trace = False
        
        for line in lines:
            # Check for thread header
            if line.startswith('"'):
                # Save previous thread
                if current_thread:
                    self.threads.append(current_thread)
                
                current_thread = self._parse_thread_header(line)
                in_stack_trace = False
                continue
            
            if current_thread is None:
                continue
                
            # Parse thread state
            state_match = self.STATE_PATTERN.search(line)
            if state_match:
                current_thread.state = state_match.group(1)
                continue
            
            # Parse stack trace lines
            stripped = line.strip()
            if stripped.startswith('at '):
                current_thread.stack_trace.append(stripped)
                in_stack_trace = True
            elif stripped.startswith('- '):
                # Lock/wait information
                self._parse_lock_info(stripped, current_thread)
                if in_stack_trace:
                    current_thread.stack_trace.append(stripped)
        
        # Don't forget the last thread
        if current_thread:
            self.threads.append(current_thread)
    
    def _parse_thread_header(self, line: str) -> ThreadInfo:
        """Parse a thread header line."""
        match = self.THREAD_HEADER_PATTERN.match(line)
        
        if match:
            return ThreadInfo(
                name=match.group('name') or 'Unknown',
                state='UNKNOWN',
                tid=match.group('tid') or '',
                nid=match.group('nid') or '',
                daemon='daemon' in line.lower(),
                priority=int(match.group('prio')) if match.group('prio') else 0
            )
        else:
            # Fallback: extract name between quotes
            name_match = re.match(r'^"([^"]+)"', line)
            name = name_match.group(1) if name_match else 'Unknown'
            return ThreadInfo(name=name, state='UNKNOWN')
    
    def _parse_lock_info(self, line: str, thread: ThreadInfo) -> None:
        """Parse lock-related information from a stack trace line."""
        # Waiting to lock
        waiting_match = self.WAITING_ON_PATTERN.search(line)
        if waiting_match:
            thread.waiting_on = waiting_match.group(1)
            # Check for owner info
            owner_match = self.LOCK_OWNER_PATTERN.search(line)
            if owner_match:
                thread.lock_owner = owner_match.group(1)
            return
        
        # Parking to wait
        parking_match = self.PARKING_PATTERN.search(line)
        if parking_match:
            thread.waiting_on = parking_match.group(1)
            return
        
        # Waiting on monitor
        monitor_match = self.WAITING_ON_MONITOR_PATTERN.search(line)
        if monitor_match:
            thread.waiting_on = monitor_match.group(1)
            return
        
        # Holding a lock
        locked_match = self.LOCKED_PATTERN.search(line)
        if locked_match:
            thread.locked_synchronizers.append(locked_match.group(1))
    
    def _detect_deadlocks(self, lines: List[str]) -> None:
        """Detect deadlock sections in the thread dump."""
        in_deadlock_section = False
        deadlock_threads = []
        deadlock_desc_lines = []
        
        for line in lines:
            if 'Found' in line and 'deadlock' in line.lower():
                in_deadlock_section = True
                deadlock_desc_lines = [line]
                continue
            
            if in_deadlock_section:
                if line.strip() == '' and deadlock_threads:
                    # End of deadlock section
                    self.deadlocks.append(DeadlockInfo(
                        threads=deadlock_threads.copy(),
                        description='\n'.join(deadlock_desc_lines)
                    ))
                    deadlock_threads = []
                    deadlock_desc_lines = []
                    in_deadlock_section = False
                elif line.startswith('"'):
                    # Thread name in deadlock
                    name_match = re.match(r'^"([^"]+)"', line)
                    if name_match:
                        deadlock_threads.append(name_match.group(1))
                    deadlock_desc_lines.append(line)
                elif line.strip():
                    deadlock_desc_lines.append(line)
    
    def _find_hot_locks(self) -> List[Dict[str, Any]]:
        """Find locks that have multiple threads waiting on them."""
        lock_waiters: Dict[str, List[str]] = {}
        lock_owners: Dict[str, str] = {}
        
        for thread in self.threads:
            if thread.waiting_on:
                if thread.waiting_on not in lock_waiters:
                    lock_waiters[thread.waiting_on] = []
                lock_waiters[thread.waiting_on].append(thread.name)
                
                if thread.lock_owner:
                    lock_owners[thread.waiting_on] = thread.lock_owner
        
        hot_locks = []
        for lock_addr, waiters in lock_waiters.items():
            if len(waiters) >= 2:  # Consider "hot" if 2+ threads waiting
                hot_locks.append({
                    'lock': lock_addr,
                    'waiters': waiters,
                    'waiter_count': len(waiters),
                    'owner': lock_owners.get(lock_addr, 'Unknown')
                })
        
        # Sort by waiter count descending
        hot_locks.sort(key=lambda x: x['waiter_count'], reverse=True)
        return hot_locks
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics from parsed threads."""
        state_counts = {
            'RUNNABLE': 0,
            'BLOCKED': 0,
            'WAITING': 0,
            'TIMED_WAITING': 0,
            'NEW': 0,
            'TERMINATED': 0,
            'UNKNOWN': 0
        }
        
        for thread in self.threads:
            state = thread.state if thread.state in state_counts else 'UNKNOWN'
            state_counts[state] += 1
        
        # Find threads potentially causing issues
        blocked_threads = [t.name for t in self.threads if t.state == 'BLOCKED']
        
        return {
            'total_threads': len(self.threads),
            'state_counts': state_counts,
            'runnable': state_counts['RUNNABLE'],
            'blocked': state_counts['BLOCKED'],
            'waiting': state_counts['WAITING'],
            'timed_waiting': state_counts['TIMED_WAITING'],
            'daemon_count': sum(1 for t in self.threads if t.daemon),
            'blocked_thread_names': blocked_threads[:10],  # Top 10
            'has_deadlocks': len(self.deadlocks) > 0,
            'deadlock_count': len(self.deadlocks)
        }
    
    def _thread_to_dict(self, thread: ThreadInfo) -> Dict[str, Any]:
        """Convert ThreadInfo dataclass to dictionary."""
        return {
            'name': thread.name,
            'state': thread.state,
            'tid': thread.tid,
            'nid': thread.nid,
            'daemon': thread.daemon,
            'priority': thread.priority,
            'stack_trace': thread.stack_trace,
            'waiting_on': thread.waiting_on,
            'lock_owner': thread.lock_owner,
            'locked_synchronizers': thread.locked_synchronizers
        }
    
    def get_summary_text(self) -> str:
        """
        Generate a human-readable summary suitable for LLM context.
        
        Returns:
            Formatted text summary of thread dump analysis
        """
        result = self.parse()
        summary = result['summary']
        
        lines = [
            "## JVM Thread Dump Analysis",
            "",
            f"**Total Threads:** {summary['total_threads']}",
            "",
            "### Thread States:",
            f"- RUNNABLE: {summary['runnable']}",
            f"- BLOCKED: {summary['blocked']}",
            f"- WAITING: {summary['waiting']}",
            f"- TIMED_WAITING: {summary['timed_waiting']}",
            ""
        ]
        
        # Deadlock warning
        if summary['has_deadlocks']:
            lines.append(f"⚠️ **DEADLOCK DETECTED:** {summary['deadlock_count']} deadlock(s) found!")
            for dl in result['deadlocks']:
                lines.append(f"  - Threads involved: {', '.join(dl['threads'])}")
            lines.append("")
        
        # Hot locks
        if result['hot_locks']:
            lines.append("### Lock Contention (Hot Locks):")
            for lock in result['hot_locks'][:5]:  # Top 5
                lines.append(f"- Lock `{lock['lock']}`: {lock['waiter_count']} threads waiting")
                lines.append(f"  - Owner: {lock['owner']}")
                lines.append(f"  - Waiters: {', '.join(lock['waiters'][:3])}{'...' if len(lock['waiters']) > 3 else ''}")
            lines.append("")
        
        # Blocked threads
        if summary['blocked_thread_names']:
            lines.append("### Blocked Threads:")
            for name in summary['blocked_thread_names'][:5]:
                lines.append(f"- {name}")
            lines.append("")
        
        return '\n'.join(lines)
