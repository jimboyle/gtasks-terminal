"""
CLI command for importing existing Google Tasks tags as regular tags.
"""

import click
from pathlib import Path
from typing import Optional
import sys

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"


@click.command('import-tags', help='Import existing Google Tasks tags as regular tags')
@click.option('--data-dir', type=str, help='Directory containing Google Tasks data (default: ~/.gtasks)')
@click.option('--dry-run', is_flag=True, help='Show what would be imported without saving')
@click.option('--stats', is_flag=True, help='Show statistics about imported tags')
@click.option('--delete', type=str, help='Delete a specific tag')
@click.option('--update', nargs=2, metavar=('TAG', 'COLOR'), help='Update tag color (e.g., --update mytag #3b82f6)')
def import_tags_command(
    data_dir: Optional[str],
    dry_run: bool,
    stats: bool,
    delete: Optional[str],
    update: Optional[tuple]
):
    """Import existing Google Tasks tags as regular tags."""
    
    # Import the importer module
    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        from import_existing_tags import TagImporter, load_google_tasks_data
    except ImportError as e:
        click.echo(f"Error: Could not import tag importer: {e}", err=True)
        return
    
    # Initialize importer
    importer = TagImporter(data_dir)
    
    if stats:
        # Show statistics
        stats_data = importer.get_tag_statistics()
        
        click.echo("\n📊 Tag Statistics:")
        click.echo(f"  Total imported tags: {stats_data['total_tags']}")
        click.echo(f"  Total tag usage: {stats_data['total_usage']}")
        
        if stats_data['most_used_tags']:
            click.echo("\n🔥 Most used tags:")
            for item in stats_data['most_used_tags']:
                click.echo(f"  - {item['tag']}: {item['count']} occurrences")
        
        if stats_data['recently_imported_tags']:
            click.echo("\n🕐 Recently imported tags:")
            for item in stats_data['recently_imported_tags']:
                click.echo(f"  - {item['tag']}")
        
        return
    
    if delete:
        # Delete a specific tag
        if importer.delete_tag(delete, dry_run=dry_run):
            click.secho(f"✓ Deleted tag: {delete}", fg='green')
        else:
            click.secho(f"✗ Tag not found: {delete}", fg='red')
        return
    
    if update:
        # Update tag metadata
        tag_name, color = update
        if importer.update_tag_metadata(tag_name, {'color': color}, dry_run=dry_run):
            click.secho(f"✓ Updated tag color: {tag_name} -> {color}", fg='green')
        else:
            click.secho(f"✗ Tag not found: {tag_name}", fg='red')
        return
    
    # Default: import tags from Google Tasks
    # Use account-specific directory if available
    if not data_dir:
        import os
        if os.environ.get('GTASKS_CONFIG_DIR'):
            data_dir = os.environ['GTASKS_CONFIG_DIR']
    
    click.echo("Loading Google Tasks data...")
    tasks = load_google_tasks_data(data_dir)
    
    if not tasks:
        click.secho("No tasks found to import tags from.", fg='yellow')
        click.echo(f"Please ensure Google Tasks data exists in {data_dir or '~/.gtasks'}/tasklists/")
        return
    
    click.echo(f"Loaded {len(tasks)} tasks")
    
    # Import tags
    importer.import_tags(tasks, dry_run=dry_run)


if __name__ == '__main__':
    import_tags_command()
