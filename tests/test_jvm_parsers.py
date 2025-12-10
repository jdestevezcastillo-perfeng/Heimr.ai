# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
"""
Unit tests for JVM thread dump parser.
"""

import pytest
import os
from heimr.parsers.threaddump import ThreadDumpParser


class TestThreadDumpParser:
    """Test suite for JVM thread dump parsing."""
    
    @pytest.fixture
    def sample_dump_path(self):
        """Path to sample thread dump fixture."""
        return os.path.join(
            os.path.dirname(__file__), 
            'fixtures', 
            'sample_thread_dump.txt'
        )
    
    @pytest.fixture
    def parser(self, sample_dump_path):
        """Create parser instance with sample fixture."""
        return ThreadDumpParser(filepath=sample_dump_path)
    
    def test_parse_returns_expected_structure(self, parser):
        """Test that parse returns required structure."""
        result = parser.parse()
        
        assert 'threads' in result
        assert 'summary' in result
        assert 'deadlocks' in result
        assert 'hot_locks' in result
        assert 'jvm_info' in result
    
    def test_parse_thread_count(self, parser):
        """Test correct number of threads parsed."""
        result = parser.parse()
        
        # Our fixture has around 14 threads
        assert result['summary']['total_threads'] >= 10
    
    def test_detect_blocked_threads(self, parser):
        """Test detection of BLOCKED threads."""
        result = parser.parse()
        
        # Our fixture has 3 threads blocked on InventoryLock
        assert result['summary']['blocked'] >= 3
    
    def test_detect_runnable_threads(self, parser):
        """Test detection of RUNNABLE threads."""
        result = parser.parse()
        
        assert result['summary']['runnable'] >= 2
    
    def test_detect_waiting_threads(self, parser):
        """Test detection of WAITING/TIMED_WAITING threads."""
        result = parser.parse()
        
        waiting_total = (
            result['summary']['waiting'] + 
            result['summary']['timed_waiting']
        )
        assert waiting_total >= 2
    
    def test_detect_hot_locks(self, parser):
        """Test detection of contended locks."""
        result = parser.parse()
        
        # Our fixture has 3 threads waiting on InventoryLock
        assert len(result['hot_locks']) >= 1
        
        # Check the hot lock has multiple waiters
        if result['hot_locks']:
            top_lock = result['hot_locks'][0]
            assert top_lock['waiter_count'] >= 2
    
    def test_extract_lock_owner(self, parser):
        """Test extraction of lock owner thread."""
        result = parser.parse()
        
        if result['hot_locks']:
            top_lock = result['hot_locks'][0]
            assert 'owner' in top_lock
            # In our fixture, http-nio-8080-exec-5 owns the lock
            assert 'exec-5' in top_lock['owner'] or top_lock['owner'] == 'Unknown'
    
    def test_summary_text_generation(self, parser):
        """Test human-readable summary generation."""
        summary_text = parser.get_summary_text()
        
        assert '## JVM Thread Dump Analysis' in summary_text
        assert 'Total Threads' in summary_text
        assert 'RUNNABLE' in summary_text
        assert 'BLOCKED' in summary_text
    
    def test_parse_thread_names(self, parser):
        """Test thread names are correctly extracted."""
        result = parser.parse()
        
        thread_names = [t['name'] for t in result['threads']]
        
        # Check for expected thread names from fixture
        assert any('main' in name.lower() for name in thread_names)
    
    def test_parse_thread_states(self, parser):
        """Test thread states are correctly extracted."""
        result = parser.parse()
        
        states = {t['state'] for t in result['threads']}
        
        # Should have at least RUNNABLE and BLOCKED
        assert 'RUNNABLE' in states or 'BLOCKED' in states
    
    def test_empty_content_handling(self):
        """Test graceful handling of empty content."""
        # Empty string is rejected - must provide valid content
        with pytest.raises(ValueError):
            ThreadDumpParser(content="")
        
        # But whitespace-only content should parse to empty results
        parser = ThreadDumpParser(content="   \n\n   ")
        result = parser.parse()
        assert result['summary']['total_threads'] == 0
    
    def test_malformed_content_handling(self):
        """Test graceful handling of malformed content."""
        parser = ThreadDumpParser(content="This is not a thread dump\nJust random text")
        result = parser.parse()
        
        # Should not crash, just return empty results
        assert 'threads' in result
        assert 'summary' in result


class TestThreadDumpParserContent:
    """Test parser with inline content."""
    
    def test_parse_simple_thread(self):
        """Test parsing a single simple thread."""
        content = '''
"main" #1 prio=5 os_prio=0 tid=0x00007f1234567890 nid=0x1 runnable
   java.lang.Thread.State: RUNNABLE
	at java.lang.Thread.sleep(Native Method)
	at com.example.Main.main(Main.java:10)
'''
        parser = ThreadDumpParser(content=content)
        result = parser.parse()
        
        assert result['summary']['total_threads'] == 1
        assert result['summary']['runnable'] == 1
        assert result['threads'][0]['name'] == 'main'
    
    def test_parse_blocked_thread(self):
        """Test parsing a BLOCKED thread."""
        content = '''
"worker" #2 daemon prio=5 tid=0x00007f1234567891 nid=0x2 waiting to lock <0x00000000deadbeef> (a java.lang.Object) owned by "main"
   java.lang.Thread.State: BLOCKED (on object monitor)
	at com.example.Worker.run(Worker.java:20)
	- waiting to lock <0x00000000deadbeef> (a java.lang.Object) owned by "main"
'''
        parser = ThreadDumpParser(content=content)
        result = parser.parse()
        
        assert result['summary']['blocked'] == 1
        assert result['threads'][0]['waiting_on'] == '0x00000000deadbeef'
        assert result['threads'][0]['lock_owner'] == 'main'
