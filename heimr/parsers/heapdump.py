# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
JVM Heap Dump Parser for Heimr.

Parses jmap -histo output or similar heap histogram formats
to extract memory usage statistics.
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ClassHistogramEntry:
    """Represents a single class entry in the heap histogram."""
    rank: int
    instances: int
    bytes: int
    class_name: str


class HeapDumpParser:
    """
    Parses JVM heap histograms (jmap -histo output format).
    
    Supports:
    - jmap -histo output
    - jcmd <pid> GC.class_histogram output
    - Eclipse MAT exported histograms
    
    Example usage:
        parser = HeapDumpParser(filepath='/path/to/histogram.txt')
        result = parser.parse()
        print(result['heap_summary'])
    """
    
    # Regex for standard jmap -histo format:
    # num     #instances         #bytes  class name
    #   1:       1234567       98765432  [B
    HISTO_LINE_PATTERN = re.compile(
        r'^\s*(\d+):\s+(\d+)\s+(\d+)\s+(.+)$'
    )
    
    # Alternative format (some JDK versions):
    # num   instances    bytes  class name
    HISTO_ALT_PATTERN = re.compile(
        r'^\s*(\d+)\s+(\d+)\s+(\d+)\s+(.+)$'
    )
    
    # Total line pattern
    TOTAL_PATTERN = re.compile(
        r'^Total\s+(\d+)\s+(\d+)',
        re.IGNORECASE
    )
    
    # Class name translations for primitive arrays
    PRIMITIVE_ARRAY_NAMES = {
        '[B': 'byte[]',
        '[C': 'char[]',
        '[D': 'double[]',
        '[F': 'float[]',
        '[I': 'int[]',
        '[J': 'long[]',
        '[S': 'short[]',
        '[Z': 'boolean[]',
    }
    
    def __init__(self, filepath: str = None, content: str = None):
        """
        Initialize parser with either a file path or raw content.
        
        Args:
            filepath: Path to heap histogram file
            content: Raw histogram content string
        """
        if filepath:
            with open(filepath, 'r') as f:
                self.content = f.read()
        elif content:
            self.content = content
        else:
            raise ValueError("Either filepath or content must be provided")
        
        self.entries: List[ClassHistogramEntry] = []
        self.total_instances: int = 0
        self.total_bytes: int = 0
        
    def parse(self) -> Dict[str, Any]:
        """
        Parse the heap histogram and return structured data.
        
        Returns:
            Dictionary containing:
            - heap_summary: Total bytes, instances, and top classes
            - top_classes: Top N memory consumers
            - potential_leaks: Classes with unusually high instance counts
        """
        lines = self.content.split('\n')
        self._parse_histogram(lines)
        
        return {
            'heap_summary': self._generate_summary(),
            'top_classes': self._get_top_classes(20),
            'top_by_instances': self._get_top_by_instances(10),
            'potential_leaks': self._detect_potential_leaks(),
            'array_usage': self._analyze_arrays()
        }
    
    def _parse_histogram(self, lines: List[str]) -> None:
        """Parse histogram lines."""
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for total line
            total_match = self.TOTAL_PATTERN.match(line)
            if total_match:
                self.total_instances = int(total_match.group(1))
                self.total_bytes = int(total_match.group(2))
                continue
            
            # Try standard format
            match = self.HISTO_LINE_PATTERN.match(line)
            if not match:
                match = self.HISTO_ALT_PATTERN.match(line)
            
            if match:
                entry = ClassHistogramEntry(
                    rank=int(match.group(1)),
                    instances=int(match.group(2)),
                    bytes=int(match.group(3)),
                    class_name=self._normalize_class_name(match.group(4).strip())
                )
                self.entries.append(entry)
    
    def _normalize_class_name(self, class_name: str) -> str:
        """Convert JVM internal class names to readable format."""
        # Handle primitive arrays
        if class_name in self.PRIMITIVE_ARRAY_NAMES:
            return self.PRIMITIVE_ARRAY_NAMES[class_name]
        
        # Handle object arrays: [Ljava/lang/String; -> String[]
        if class_name.startswith('[L') and class_name.endswith(';'):
            inner = class_name[2:-1].replace('/', '.')
            # Get simple name
            simple = inner.split('.')[-1]
            return f"{simple}[]"
        
        # Handle multi-dimensional arrays
        if class_name.startswith('[['):
            depth = len(class_name) - len(class_name.lstrip('['))
            inner = class_name[depth:]
            if inner in self.PRIMITIVE_ARRAY_NAMES:
                base = self.PRIMITIVE_ARRAY_NAMES[inner].replace('[]', '')
            elif inner.startswith('L') and inner.endswith(';'):
                base = inner[1:-1].replace('/', '.').split('.')[-1]
            else:
                base = inner
            return base + '[]' * depth
        
        # Regular class: java/lang/String -> String
        if '/' in class_name:
            class_name = class_name.replace('/', '.')
        
        return class_name.split('.')[-1] if '.' in class_name else class_name
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics."""
        # Calculate totals if not found in Total line
        if self.total_instances == 0:
            self.total_instances = sum(e.instances for e in self.entries)
        if self.total_bytes == 0:
            self.total_bytes = sum(e.bytes for e in self.entries)
        
        return {
            'total_bytes': self.total_bytes,
            'total_bytes_mb': round(self.total_bytes / (1024 * 1024), 2),
            'total_instances': self.total_instances,
            'unique_classes': len(self.entries),
            'avg_bytes_per_instance': round(self.total_bytes / max(self.total_instances, 1), 2)
        }
    
    def _get_top_classes(self, n: int = 20) -> List[Dict[str, Any]]:
        """Get top N classes by byte usage."""
        sorted_entries = sorted(self.entries, key=lambda x: x.bytes, reverse=True)
        
        result = []
        for entry in sorted_entries[:n]:
            pct = (entry.bytes / max(self.total_bytes, 1)) * 100
            result.append({
                'class': entry.class_name,
                'instances': entry.instances,
                'bytes': entry.bytes,
                'bytes_mb': round(entry.bytes / (1024 * 1024), 2),
                'percentage': round(pct, 2)
            })
        return result
    
    def _get_top_by_instances(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get top N classes by instance count."""
        sorted_entries = sorted(self.entries, key=lambda x: x.instances, reverse=True)
        
        result = []
        for entry in sorted_entries[:n]:
            pct = (entry.instances / max(self.total_instances, 1)) * 100
            avg_size = entry.bytes / max(entry.instances, 1)
            result.append({
                'class': entry.class_name,
                'instances': entry.instances,
                'bytes': entry.bytes,
                'avg_size': round(avg_size, 2),
                'percentage': round(pct, 2)
            })
        return result
    
    def _detect_potential_leaks(self) -> List[Dict[str, Any]]:
        """
        Detect classes that might indicate memory leaks.
        
        Heuristics:
        - High instance count of collection types
        - Large byte arrays that could be buffers
        - String accumulation
        """
        suspects = []
        
        # Collections with high instance counts
        collection_patterns = ['HashMap', 'ArrayList', 'LinkedList', 'HashSet', 'ConcurrentHashMap']
        
        for entry in self.entries:
            # Check for collection types with many instances
            for pattern in collection_patterns:
                if pattern in entry.class_name and entry.instances > 10000:
                    suspects.append({
                        'class': entry.class_name,
                        'instances': entry.instances,
                        'bytes_mb': round(entry.bytes / (1024 * 1024), 2),
                        'reason': f'High instance count of {pattern}'
                    })
                    break
            
            # Large byte arrays (potential buffer accumulation)
            if entry.class_name == 'byte[]' and entry.bytes > 100 * 1024 * 1024:  # >100MB
                suspects.append({
                    'class': entry.class_name,
                    'instances': entry.instances,
                    'bytes_mb': round(entry.bytes / (1024 * 1024), 2),
                    'reason': 'Large byte array accumulation (possible buffer leak)'
                })
            
            # String accumulation
            if entry.class_name == 'String' and entry.instances > 1000000:  # >1M strings
                suspects.append({
                    'class': entry.class_name,
                    'instances': entry.instances,
                    'bytes_mb': round(entry.bytes / (1024 * 1024), 2),
                    'reason': 'High String instance count (check for String concatenation in loops)'
                })
        
        return suspects
    
    def _analyze_arrays(self) -> Dict[str, Any]:
        """Analyze array usage patterns."""
        array_entries = [e for e in self.entries if '[]' in e.class_name or e.class_name.startswith('[')]
        
        total_array_bytes = sum(e.bytes for e in array_entries)
        
        return {
            'total_array_bytes': total_array_bytes,
            'total_array_bytes_mb': round(total_array_bytes / (1024 * 1024), 2),
            'array_percentage': round((total_array_bytes / max(self.total_bytes, 1)) * 100, 2),
            'array_types': len(array_entries)
        }
    
    def get_summary_text(self) -> str:
        """
        Generate a human-readable summary suitable for LLM context.
        
        Returns:
            Formatted text summary of heap analysis
        """
        result = self.parse()
        summary = result['heap_summary']
        
        lines = [
            "## JVM Heap Analysis",
            "",
            f"**Total Heap Usage:** {summary['total_bytes_mb']} MB",
            f"**Total Instances:** {summary['total_instances']:,}",
            f"**Unique Classes:** {summary['unique_classes']}",
            "",
            "### Top Memory Consumers:"
        ]
        
        for i, cls in enumerate(result['top_classes'][:10], 1):
            lines.append(f"{i}. `{cls['class']}`: {cls['bytes_mb']} MB ({cls['percentage']}%) - {cls['instances']:,} instances")
        
        lines.append("")
        
        # Potential leaks
        if result['potential_leaks']:
            lines.append("### ⚠️ Potential Memory Leak Indicators:")
            for leak in result['potential_leaks']:
                lines.append(f"- `{leak['class']}`: {leak['bytes_mb']} MB - {leak['reason']}")
            lines.append("")
        
        # Array analysis
        arrays = result['array_usage']
        lines.append(f"### Array Usage: {arrays['total_array_bytes_mb']} MB ({arrays['array_percentage']}% of heap)")
        
        return '\n'.join(lines)
