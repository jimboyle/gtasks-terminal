#!/usr/bin/env python3
"""
Import existing Google Tasks tags as regular tags.

This script extracts all tags from existing Google Tasks and imports them
as regular tags (not @account tags) to make them available in the dashboard.
"""

import json
import os
import sys
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from gtasks_cli.utils.tag_extractor import extract_tags_from_task
from gtasks_cli.core.task_manager import TaskManager


class TagImporter:
    """Import existing Google Tasks tags as regular tags."""
    
    def __init__(self, data_dir: str = None):
        """Initialize the tag importer.
        
        Args:
            data_dir: Directory containing task data. Defaults to ~/.gtasks.
        """
        self.data_dir = data_dir or os.path.expanduser("~/.gtasks")
        self.tags_file = os.path.join(self.data_dir, "imported_tags.json")
        self.tag_usage_file = os.path.join(self.data_dir, "tag_usage.json")
        
        # Track imported tags and their usage
        self.imported_tags: Dict[str, Dict] = {}
        self.tag_usage: Dict[str, int] = defaultdict(int)
        
        # Load existing data
        self._load_imported_tags()
        self._load_tag_usage()
    
    def _load_imported_tags(self) -> None:
        """Load previously imported tags from file."""
        if os.path.exists(self.tags_file):
            try:
                with open(self.tags_file, 'r') as f:
                    self.imported_tags = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load existing tags file: {e}")
                self.imported_tags = {}
    
    def _load_tag_usage(self) -> None:
        """Load tag usage statistics from file."""
        if os.path.exists(self.tag_usage_file):
            try:
                with open(self.tag_usage_file, 'r') as f:
                    self.tag_usage = defaultdict(int, json.load(f))
            except Exception as e:
                print(f"Warning: Could not load tag usage file: {e}")
                self.tag_usage = defaultdict(int)
    
    def _save_imported_tags(self) -> None:
        """Save imported tags to file."""
        os.makedirs(os.path.dirname(self.tags_file), exist_ok=True)
        with open(self.tags_file, 'w') as f:
            json.dump(self.imported_tags, f, indent=2)
    
    def _save_tag_usage(self) -> None:
        """Save tag usage statistics to file."""
        os.makedirs(os.path.dirname(self.tag_usage_file), exist_ok=True)
        with open(self.tag_usage_file, 'w') as f:
            json.dump(dict(self.tag_usage), f, indent=2)
    
    def extract_tags_from_google_tasks(self, tasks: List[Dict]) -> Tuple[Set[str], Dict[str, int]]:
        """Extract all unique tags from Google Tasks and count their usage.
        
        Args:
            tasks: List of task dictionaries from Google Tasks.
            
        Returns:
            Tuple of (set of unique tags, dict of tag usage counts)
        """
        unique_tags = set()
        tag_counts = defaultdict(int)
        
        for task in tasks:
            # Extract tags from task fields
            tags = extract_tags_from_task(task)
            
            for tag in tags:
                # Skip @account tags - these are for user connections
                if tag.startswith('@'):
                    continue
                    
                # Normalize tag (lowercase, strip whitespace)
                normalized_tag = tag.lower().strip()
                
                if normalized_tag:
                    unique_tags.add(normalized_tag)
                    tag_counts[normalized_tag] += 1
        
        return unique_tags, dict(tag_counts)
    
    def import_tags(self, tasks: List[Dict], dry_run: bool = False) -> Dict[str, int]:
        """Import tags from Google Tasks.
        
        Args:
            tasks: List of task dictionaries from Google Tasks.
            dry_run: If True, don't actually save anything.
            
        Returns:
            Dict of imported tags with their usage counts.
        """
        print("Extracting tags from Google Tasks...")
        
        unique_tags, tag_counts = self.extract_tags_from_google_tasks(tasks)
        
        print(f"Found {len(unique_tags)} unique tags")
        print(f"Total tag occurrences: {sum(tag_counts.values())}")
        
        # Track what will be imported
        new_tags = {}
        updated_tags = {}
        unchanged_tags = {}
        
        for tag in sorted(unique_tags):
            if tag not in self.imported_tags:
                new_tags[tag] = {
                    'first_imported': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'usage_count': tag_counts[tag],
                    'color': self._get_random_color(),
                    'description': ''
                }
            elif self.imported_tags[tag]['usage_count'] != tag_counts[tag]:
                updated_tags[tag] = {
                    'first_imported': self.imported_tags[tag]['first_imported'],
                    'last_updated': datetime.now().isoformat(),
                    'usage_count': tag_counts[tag],
                    'color': self.imported_tags[tag].get('color', self._get_random_color()),
                    'description': self.imported_tags[tag].get('description', '')
                }
            else:
                unchanged_tags[tag] = self.imported_tags[tag]
        
        # Print summary
        print(f"\nImport Summary:")
        print(f"  New tags: {len(new_tags)}")
        print(f"  Updated tags: {len(updated_tags)}")
        print(f"  Unchanged tags: {len(unchanged_tags)}")
        
        if new_tags:
            print(f"\nNew tags to import:")
            for tag in sorted(new_tags.keys())[:10]:  # Show first 10
                print(f"  - {tag} ({new_tags[tag]['usage_count']} occurrences)")
            if len(new_tags) > 10:
                print(f"  ... and {len(new_tags) - 10} more")
        
        if not dry_run:
            # Merge changes
            self.imported_tags.update(new_tags)
            self.imported_tags.update(updated_tags)
            
            # Update usage counts
            for tag, count in tag_counts.items():
                self.tag_usage[tag] = count
            
            # Save to files
            self._save_imported_tags()
            self._save_tag_usage()
            
            print(f"\n✓ Imported {len(new_tags)} new tags")
            print(f"✓ Updated {len(updated_tags)} tags")
            print(f"✓ Tags saved to {self.tags_file}")
        
        return {tag: info['usage_count'] for tag, info in {**new_tags, **updated_tags, **unchanged_tags}.items()}
    
    def _get_random_color(self) -> str:
        """Get a random color for a tag.
        
        Returns:
            Random color from a predefined palette.
        """
        colors = [
            '#3b82f6',  # blue
            '#10b981',  # green
            '#f59e0b',  # yellow
            '#ef4444',  # red
            '#8b5cf6',  # purple
            '#ec4899',  # pink
            '#6b7280',  # gray
        ]
        import random
        return random.choice(colors)
    
    def get_imported_tags(self) -> Dict[str, Dict]:
        """Get all imported tags.
        
        Returns:
            Dict of imported tags with their metadata.
        """
        return self.imported_tags
    
    def get_tag_by_name(self, tag_name: str) -> Dict:
        """Get a specific tag by name.
        
        Args:
            tag_name: Name of the tag to retrieve.
            
        Returns:
            Tag metadata dict or None if not found.
        """
        return self.imported_tags.get(tag_name.lower())
    
    def update_tag_metadata(self, tag_name: str, metadata: Dict, dry_run: bool = False) -> bool:
        """Update metadata for a specific tag.
        
        Args:
            tag_name: Name of the tag to update.
            metadata: Dict of metadata to update.
            dry_run: If True, don't actually save anything.
            
        Returns:
            True if tag was found and updated, False otherwise.
        """
        normalized_name = tag_name.lower()
        
        if normalized_name not in self.imported_tags:
            return False
        
        if not dry_run:
            self.imported_tags[normalized_name].update(metadata)
            self.imported_tags[normalized_name]['last_updated'] = datetime.now().isoformat()
            self._save_imported_tags()
        
        return True
    
    def delete_tag(self, tag_name: str, dry_run: bool = False) -> bool:
        """Delete a specific tag.
        
        Args:
            tag_name: Name of the tag to delete.
            dry_run: If True, don't actually save anything.
            
        Returns:
            True if tag was found and deleted, False otherwise.
        """
        normalized_name = tag_name.lower()
        
        if normalized_name not in self.imported_tags:
            return False
        
        if not dry_run:
            del self.imported_tags[normalized_name]
            if normalized_name in self.tag_usage:
                del self.tag_usage[normalized_name]
            self._save_imported_tags()
            self._save_tag_usage()
        
        return True
    
    def get_tag_statistics(self) -> Dict:
        """Get statistics about imported tags.
        
        Returns:
            Dict with tag statistics.
        """
        total_tags = len(self.imported_tags)
        total_usage = sum(self.tag_usage.values())
        
        # Most used tags
        most_used = sorted(self.tag_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Recently imported tags
        recently_imported = sorted(
            self.imported_tags.items(),
            key=lambda x: x[1].get('first_imported', ''),
            reverse=True
        )[:5]
        
        return {
            'total_tags': total_tags,
            'total_usage': total_usage,
            'most_used_tags': [{'tag': tag, 'count': count} for tag, count in most_used],
            'recently_imported_tags': [{'tag': tag, 'info': info} for tag, info in recently_imported]
        }


def load_google_tasks_data(data_dir: str = None) -> List[Dict]:
    """Load Google Tasks data from the data directory.
    
    Supports both account-aware loading (using GTASKS_CONFIG_DIR) and 
    both JSON and SQLite database formats.
    
    Args:
        data_dir: Directory containing Google Tasks data. Defaults to ~/.gtasks.
        
    Returns:
        List of task dictionaries.
    """
    # Check for account-specific configuration first
    if not data_dir:
        # Use GTASKS_CONFIG_DIR if set (account-aware)
        if os.environ.get('GTASKS_CONFIG_DIR'):
            data_dir = os.environ['GTASKS_CONFIG_DIR']
            print(f"Loading tasks from account-specific directory: {data_dir}")
        else:
            data_dir = os.path.expanduser("~/.gtasks")
    
    tasks = []
    
    # First, try to load from SQLite database (modern format)
    db_path = os.path.join(data_dir, "tasks.db")
    if os.path.exists(db_path):
        print(f"Loading tasks from SQLite database: {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Try different table schemas
            cursor.execute("SELECT * FROM tasks LIMIT 1")
            columns = [description[0] for description in cursor.description]
            
            cursor.execute("""
                SELECT id, title, description, notes, status, priority, due, 
                       created_at, modified_at, tasklist_id, project, tags
                FROM tasks
            """)
            
            for row in cursor.fetchall():
                task = dict(zip(columns, row))
                # Convert to Google Tasks API format
                task_obj = {
                    'id': task.get('id'),
                    'title': task.get('title') or '',
                    'description': task.get('description') or '',
                    'notes': task.get('notes') or '',
                    'status': task.get('status') or 'needsAction',
                    'due': task.get('due'),
                    'tags': task.get('tags', '').split(',') if task.get('tags') else []
                }
                tasks.append(task_obj)
            
            conn.close()
            print(f"Loaded {len(tasks)} tasks from SQLite database")
            
        except Exception as e:
            print(f"Warning: Could not load from SQLite database: {e}")
    
    # If no tasks loaded from SQLite, try JSON tasklists directory (legacy format)
    if not tasks:
        tasklists_dir = os.path.join(data_dir, "tasklists")
        
        if not os.path.exists(tasklists_dir):
            print(f"Warning: Tasklists directory not found: {tasklists_dir}")
            return tasks
        
        # Load all tasklists and their tasks
        for filename in os.listdir(tasklists_dir):
            if filename.endswith('.json') and not filename.startswith('.'):
                filepath = os.path.join(tasklists_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        
                        # Handle both single tasklist and multiple tasklists format
                        if isinstance(data, dict):
                            if 'tasks' in data:
                                tasks.extend(data['tasks'])
                            elif 'items' in data:
                                # Google Tasks API format
                                for tasklist in data['items']:
                                    if 'tasks' in tasklist:
                                        tasks.extend(tasklist['tasks'])
                        elif isinstance(data, list):
                            tasks.extend(data)
                            
                except Exception as e:
                    print(f"Warning: Could not load {filename}: {e}")
    
    return tasks


def main():
    """Main function to run the tag import."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import existing Google Tasks tags as regular tags')
    parser.add_argument('--data-dir', type=str, help='Directory containing Google Tasks data (default: ~/.gtasks)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be imported without saving')
    parser.add_argument('--stats', action='store_true', help='Show statistics about imported tags')
    parser.add_argument('--delete', type=str, help='Delete a specific tag')
    parser.add_argument('--update', nargs=2, metavar=('TAG', 'COLOR'), help='Update tag color (e.g., --update mytag #3b82f6)')
    
    args = parser.parse_args()
    
    # Initialize importer
    importer = TagImporter(args.data_dir)
    
    if args.stats:
        # Show statistics
        stats = importer.get_tag_statistics()
        print("\nTag Statistics:")
        print(f"  Total imported tags: {stats['total_tags']}")
        print(f"  Total tag usage: {stats['total_usage']}")
        
        if stats['most_used_tags']:
            print("\nMost used tags:")
            for item in stats['most_used_tags']:
                print(f"  - {item['tag']}: {item['count']} occurrences")
        
        if stats['recently_imported_tags']:
            print("\nRecently imported tags:")
            for item in stats['recently_imported_tags']:
                print(f"  - {item['tag']}")
        
        return
    
    if args.delete:
        # Delete a specific tag
        if importer.delete_tag(args.delete, dry_run=args.dry_run):
            print(f"✓ Deleted tag: {args.delete}")
        else:
            print(f"✗ Tag not found: {args.delete}")
        return
    
    if args.update:
        # Update tag metadata
        tag_name, color = args.update
        if importer.update_tag_metadata(tag_name, {'color': color}, dry_run=args.dry_run):
            print(f"✓ Updated tag color: {tag_name} -> {color}")
        else:
            print(f"✗ Tag not found: {tag_name}")
        return
    
    # Default: import tags from Google Tasks
    print("Loading Google Tasks data...")
    tasks = load_google_tasks_data(args.data_dir)
    
    if not tasks:
        print("No tasks found to import tags from.")
        print(f"Please ensure Google Tasks data exists in {args.data_dir or '~/.gtasks'}/tasklists/")
        return
    
    print(f"Loaded {len(tasks)} tasks")
    
    # Import tags
    importer.import_tags(tasks, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
