# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
JVM GC Log Parser for Heimr.

Parses GC logs in JDK 9+ unified logging format (-Xlog:gc*)
to extract pause times, allocation rates, and GC events.
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class GCEvent:
    """Represents a single GC event."""
    timestamp: Optional[datetime]
    uptime_seconds: float
    gc_type: str  # G1, ZGC, Parallel, etc.
    cause: str  # Allocation Failure, System.gc(), etc.
    pause_ms: float
    heap_before_mb: float
    heap_after_mb: float
    heap_max_mb: float
    is_full_gc: bool = False


class GCLogParser:
    """
    Parses JVM GC logs (JDK 9+ unified logging format).
    
    Supports:
    - G1GC logs
    - ZGC logs  
    - Parallel GC logs
    - Serial GC logs
    
    Example usage:
        parser = GCLogParser(filepath='/path/to/gc.log')
        result = parser.parse()
        print(result['summary'])
    """
    
    # Common GC log patterns
    
    # [2024-01-01T12:00:00.000+0000][0.123s][info][gc] GC(0) Pause Young...
    UNIFIED_LOG_PATTERN = re.compile(
        r'\[(?P<timestamp>[^\]]+)\]'
        r'\[(?P<uptime>[\d.]+)s\]'
        r'\[(?P<level>\w+)\]'
        r'\[gc[^\]]*\]'
        r'\s*(?P<message>.+)'
    )
    
    # GC(123) Pause Young (Normal) (G1 Evacuation Pause) 500M->200M(1024M) 15.234ms
    GC_PAUSE_PATTERN = re.compile(
        r'GC\((?P<gc_id>\d+)\)\s+'
        r'Pause\s+(?P<type>\w+)'
        r'(?:\s+\((?P<cause>[^)]+)\))?'
        r'(?:\s+\([^)]+\))?'  # Additional info
        r'\s+(?P<before>\d+)M?->(?P<after>\d+)M?\((?P<max>\d+)M?\)'
        r'\s+(?P<pause>[\d.]+)ms'
    )
    
    # Alternative format: GC(123) Pause Full (System.gc()) 500M->200M(1024M) 150.234ms
    FULL_GC_PATTERN = re.compile(
        r'GC\((?P<gc_id>\d+)\)\s+'
        r'Pause\s+Full'
        r'(?:\s+\((?P<cause>[^)]+)\))?'
        r'\s+(?P<before>\d+)M?->(?P<after>\d+)M?\((?P<max>\d+)M?\)'
        r'\s+(?P<pause>[\d.]+)ms'
    )
    
    # ZGC format: GC(123) Garbage Collection (Warmup) 500M(50%)->200M(20%)
    ZGC_PATTERN = re.compile(
        r'GC\((?P<gc_id>\d+)\)\s+'
        r'Garbage Collection'
        r'(?:\s+\((?P<cause>[^)]+)\))?'
    )
    
    # Allocation rate: Concurrent Cycle 123M->50M(1024M) 25.678ms
    CONCURRENT_PATTERN = re.compile(
        r'Concurrent\s+(?P<phase>\w+)'
        r'.*?(?P<time>[\d.]+)ms'
    )
    
    # Pause time in separate line
    PAUSE_TIME_PATTERN = re.compile(
        r'(?:Pause|pause)\s*[:=]?\s*(?P<pause>[\d.]+)\s*ms'
    )
    
    def __init__(self, filepath: str = None, content: str = None):
        """
        Initialize parser with either a file path or raw content.
        
        Args:
            filepath: Path to GC log file
            content: Raw GC log content string
        """
        if filepath:
            with open(filepath, 'r') as f:
                self.content = f.read()
        elif content:
            self.content = content
        else:
            raise ValueError("Either filepath or content must be provided")
        
        self.events: List[GCEvent] = []
        self.gc_type: str = "Unknown"
        
    def parse(self) -> Dict[str, Any]:
        """
        Parse the GC log and return structured data.
        
        Returns:
            Dictionary containing:
            - events: List of GC events
            - summary: Aggregated statistics
            - long_pauses: Pauses exceeding thresholds
            - timeline: Events over time for charting
        """
        lines = self.content.split('\n')
        self._detect_gc_type(lines)
        self._parse_events(lines)
        
        return {
            'gc_type': self.gc_type,
            'events': [self._event_to_dict(e) for e in self.events],
            'summary': self._generate_summary(),
            'long_pauses': self._find_long_pauses(),
            'timeline': self._generate_timeline()
        }
    
    def _detect_gc_type(self, lines: List[str]) -> None:
        """Detect the GC algorithm used."""
        content_sample = '\n'.join(lines[:100])
        
        if 'G1' in content_sample or 'g1gc' in content_sample.lower():
            self.gc_type = 'G1'
        elif 'ZGC' in content_sample or 'zgc' in content_sample.lower():
            self.gc_type = 'ZGC'
        elif 'Parallel' in content_sample:
            self.gc_type = 'Parallel'
        elif 'Serial' in content_sample:
            self.gc_type = 'Serial'
        elif 'Shenandoah' in content_sample:
            self.gc_type = 'Shenandoah'
    
    def _parse_events(self, lines: List[str]) -> None:
        """Parse GC events from log lines."""
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try unified log format
            unified_match = self.UNIFIED_LOG_PATTERN.match(line)
            if unified_match:
                message = unified_match.group('message')
                uptime = float(unified_match.group('uptime'))
                timestamp = self._parse_timestamp(unified_match.group('timestamp'))
                
                # Check for pause event
                pause_match = self.GC_PAUSE_PATTERN.search(message)
                if pause_match:
                    event = GCEvent(
                        timestamp=timestamp,
                        uptime_seconds=uptime,
                        gc_type=self.gc_type,
                        cause=pause_match.group('cause') or 'Normal',
                        pause_ms=float(pause_match.group('pause')),
                        heap_before_mb=float(pause_match.group('before')),
                        heap_after_mb=float(pause_match.group('after')),
                        heap_max_mb=float(pause_match.group('max')),
                        is_full_gc=False
                    )
                    self.events.append(event)
                    continue
                
                # Check for Full GC
                full_match = self.FULL_GC_PATTERN.search(message)
                if full_match:
                    event = GCEvent(
                        timestamp=timestamp,
                        uptime_seconds=uptime,
                        gc_type=self.gc_type,
                        cause=full_match.group('cause') or 'Full GC',
                        pause_ms=float(full_match.group('pause')),
                        heap_before_mb=float(full_match.group('before')),
                        heap_after_mb=float(full_match.group('after')),
                        heap_max_mb=float(full_match.group('max')),
                        is_full_gc=True
                    )
                    self.events.append(event)
                    continue
    
    def _parse_timestamp(self, ts_str: str) -> Optional[datetime]:
        """Parse timestamp from various formats."""
        formats = [
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
        ]
        
        for fmt in formats:
            try:
                # Handle timezone offset without colon
                if '+' in ts_str and ':' not in ts_str.split('+')[1]:
                    ts_str = ts_str[:-2] + ':' + ts_str[-2:]
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics."""
        if not self.events:
            return {
                'total_events': 0,
                'gc_type': self.gc_type,
                'total_pause_ms': 0,
                'avg_pause_ms': 0,
                'max_pause_ms': 0,
                'p95_pause_ms': 0,
                'p99_pause_ms': 0,
                'full_gc_count': 0
            }
        
        pauses = [e.pause_ms for e in self.events]
        pauses_sorted = sorted(pauses)
        
        p95_idx = int(len(pauses_sorted) * 0.95)
        p99_idx = int(len(pauses_sorted) * 0.99)
        
        total_time = 0
        if len(self.events) >= 2:
            total_time = self.events[-1].uptime_seconds - self.events[0].uptime_seconds
        
        total_pause = sum(pauses)
        
        return {
            'total_events': len(self.events),
            'gc_type': self.gc_type,
            'total_pause_ms': round(total_pause, 2),
            'total_pause_seconds': round(total_pause / 1000, 2),
            'avg_pause_ms': round(sum(pauses) / len(pauses), 2),
            'max_pause_ms': round(max(pauses), 2),
            'min_pause_ms': round(min(pauses), 2),
            'p95_pause_ms': round(pauses_sorted[p95_idx] if p95_idx < len(pauses_sorted) else 0, 2),
            'p99_pause_ms': round(pauses_sorted[p99_idx] if p99_idx < len(pauses_sorted) else 0, 2),
            'full_gc_count': sum(1 for e in self.events if e.is_full_gc),
            'young_gc_count': sum(1 for e in self.events if not e.is_full_gc),
            'gc_time_percentage': round((total_pause / 1000) / max(total_time, 1) * 100, 2) if total_time else 0
        }
    
    def _find_long_pauses(self, threshold_ms: float = 200) -> List[Dict[str, Any]]:
        """Find GC pauses exceeding threshold."""
        long_pauses = []
        
        for event in self.events:
            if event.pause_ms >= threshold_ms:
                long_pauses.append({
                    'uptime_seconds': event.uptime_seconds,
                    'pause_ms': event.pause_ms,
                    'cause': event.cause,
                    'is_full_gc': event.is_full_gc,
                    'heap_before_mb': event.heap_before_mb,
                    'heap_after_mb': event.heap_after_mb,
                    'freed_mb': event.heap_before_mb - event.heap_after_mb
                })
        
        # Sort by pause time descending
        long_pauses.sort(key=lambda x: x['pause_ms'], reverse=True)
        return long_pauses[:20]  # Top 20
    
    def _generate_timeline(self) -> List[Dict[str, Any]]:
        """Generate timeline data for charting."""
        return [
            {
                'uptime_seconds': e.uptime_seconds,
                'pause_ms': e.pause_ms,
                'heap_before_mb': e.heap_before_mb,
                'heap_after_mb': e.heap_after_mb,
                'is_full_gc': e.is_full_gc
            }
            for e in self.events
        ]
    
    def _event_to_dict(self, event: GCEvent) -> Dict[str, Any]:
        """Convert GCEvent to dictionary."""
        return {
            'timestamp': event.timestamp.isoformat() if event.timestamp else None,
            'uptime_seconds': event.uptime_seconds,
            'gc_type': event.gc_type,
            'cause': event.cause,
            'pause_ms': event.pause_ms,
            'heap_before_mb': event.heap_before_mb,
            'heap_after_mb': event.heap_after_mb,
            'heap_max_mb': event.heap_max_mb,
            'is_full_gc': event.is_full_gc,
            'freed_mb': event.heap_before_mb - event.heap_after_mb
        }
    
    def get_summary_text(self) -> str:
        """
        Generate a human-readable summary suitable for LLM context.
        
        Returns:
            Formatted text summary of GC analysis
        """
        result = self.parse()
        summary = result['summary']
        
        lines = [
            "## JVM Garbage Collection Analysis",
            "",
            f"**GC Algorithm:** {summary['gc_type']}",
            f"**Total GC Events:** {summary['total_events']}",
            f"**Total GC Pause Time:** {summary['total_pause_seconds']}s ({summary['gc_time_percentage']}% of runtime)",
            "",
            "### Pause Statistics:",
            f"- Average: {summary['avg_pause_ms']}ms",
            f"- P95: {summary['p95_pause_ms']}ms",
            f"- P99: {summary['p99_pause_ms']}ms",
            f"- Max: {summary['max_pause_ms']}ms",
            "",
            f"**Full GC Count:** {summary['full_gc_count']}",
            f"**Young GC Count:** {summary['young_gc_count']}",
            ""
        ]
        
        # Long pauses warning
        long_pauses = result['long_pauses']
        if long_pauses:
            lines.append(f"### ⚠️ Long Pauses (>{200}ms):")
            for pause in long_pauses[:5]:
                lines.append(
                    f"- {pause['pause_ms']}ms at {pause['uptime_seconds']}s "
                    f"({'Full GC' if pause['is_full_gc'] else 'Young GC'}) "
                    f"- freed {pause['freed_mb']:.0f}MB"
                )
            lines.append("")
        
        # Full GC warning
        if summary['full_gc_count'] > 0:
            lines.append(f"⚠️ **Warning:** {summary['full_gc_count']} Full GC events detected. "
                        "Full GCs cause longer pauses and may indicate memory pressure.")
        
        return '\n'.join(lines)
