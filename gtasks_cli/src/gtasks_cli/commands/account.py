#!/usr/bin/env python3
"""
Account management commands for Google Tasks CLI
"""

import click
import os
from pathlib import Path
from gtasks_cli.utils.logger import setup_logger

logger = setup_logger(__name__)


@click.group()
def account():
    """Manage Google Tasks accounts"""
    pass


@account.command()
@click.argument('account_name')
@click.option('--global', 'global_setting', is_flag=True, 
              help='Set as global default account (stored in config)')
def use(account_name, global_setting):
    """Set the default account for the current session or globally"""
    if global_setting:
        # Store in config for global default
        from gtasks_cli.storage.config_manager import ConfigManager
        config = ConfigManager.get_global_config()
        config.set('default_account', account_name)
        click.echo(f"✅ Global default account set to '{account_name}'")
    else:
        # Save current account to a file to persist as the active account
        current_account_file = os.path.join(os.path.expanduser("~"), ".gtasks", ".current_account")
        os.makedirs(os.path.dirname(current_account_file), exist_ok=True)
        with open(current_account_file, 'w') as f:
            f.write(account_name)
        click.echo(f"✅ Default account for current session set to '{account_name}'")


@account.command()
def list():
    """List all configured accounts"""
    from gtasks_cli.storage.config_manager import ConfigManager
    
    # Get accounts from configuration
    config = ConfigManager()
    configured_accounts = config.get('accounts', {})
    
    # Get accounts from directory structure
    gtasks_dir = Path.home() / '.gtasks'
    
    current_account = None
    current_account_file = gtasks_dir / ".current_account"
    if current_account_file.exists():
        with open(current_account_file, 'r') as f:
            current_account = f.read().strip()
            
    if gtasks_dir.exists():
        account_dirs = [d.name for d in gtasks_dir.iterdir() if d.is_dir() and d.name not in ('default', 'logs') and not d.name.startswith('.')]
        if account_dirs:
            click.echo("Available accounts:")
            # Use global config to get default account
            global_config = ConfigManager.get_global_config()
            default_account = global_config.get('default_account')
            for account in account_dirs:
                labels = []
                if account == current_account:
                    labels.append("current")
                if account == default_account:
                    labels.append("global default")
                
                label_str = f" ({', '.join(labels)})" if labels else ""
                click.echo(f"  * {account}{label_str}")
            return
    
    if configured_accounts:
        click.echo("Configured accounts:")
        # Use global config to get default account
        global_config = ConfigManager.get_global_config()
        default_account = global_config.get('default_account')
        for account in configured_accounts:
            labels = []
            if account == current_account:
                labels.append("current")
            if account == default_account:
                labels.append("global default")
            
            label_str = f" ({', '.join(labels)})" if labels else ""
            click.echo(f"  * {account}{label_str}")
    else:
        click.echo("No accounts configured yet.")


@account.command()
def current():
    """Show the currently active account"""
    # Check session default from environment first
    session_default = os.environ.get('GTASKS_DEFAULT_ACCOUNT')
    if session_default:
        click.echo(f"Current session account (env): {session_default}")
        return
    
    # Check current account file
    current_account_file = os.path.join(os.path.expanduser("~"), ".gtasks", ".current_account")
    if os.path.exists(current_account_file):
        with open(current_account_file, 'r') as f:
            current_account = f.read().strip()
            if current_account:
                click.echo(f"Current session account: {current_account}")
                return
    
    # Check global default
    from gtasks_cli.storage.config_manager import ConfigManager
    config = ConfigManager.get_global_config()
    global_default = config.get('default_account')
    if global_default:
        click.echo(f"Global default account: {global_default}")
        return
    
    click.echo("No default account set")


@account.command()
@click.argument('name', required=False)
@click.option('--name', '-n', 'option_name', help='Account name')
@click.option('--credentials', '-c', help='Path to credentials JSON file')
@click.option('--auth/--no-auth', default=False, help='Run authentication flow immediately')
def add(name, option_name, credentials, auth):
    """Add a new Google Tasks account"""
    account_name = name or option_name
    if not account_name:
        click.echo("❌ Error: Account name is required. Provide it as an argument or using --name option.")
        raise click.Abort()

    # Create account directory
    account_dir = Path.home() / '.gtasks' / account_name
    account_dir.mkdir(parents=True, exist_ok=True)

    # Copy credentials if provided
    if credentials:
        cred_path = Path(credentials)
        if not cred_path.exists():
            click.echo(f"❌ Error: Credentials file not found at '{credentials}'")
            raise click.Abort()
        dest_cred = account_dir / 'credentials.json'
        import shutil
        shutil.copy(cred_path, dest_cred)
        click.echo(f"  Saved credentials to '{dest_cred}'")

    # Register in global config
    from gtasks_cli.storage.config_manager import ConfigManager
    config = ConfigManager.get_global_config()
    accounts = config.get('accounts', {})
    if account_name not in accounts:
        accounts[account_name] = {'name': account_name, 'authenticated': False}
        config.set('accounts', accounts)

    click.echo(f"✅ Successfully added account '{account_name}'!")

    # Run auth if requested
    if auth:
        from gtasks_cli.integrations.google_auth import GoogleAuthManager
        auth_manager = GoogleAuthManager(account_name=account_name)
        if auth_manager.authenticate():
            accounts[account_name]['authenticated'] = True
            config.set('accounts', accounts)
            click.echo(f"✅ Successfully authenticated account '{account_name}'!")
        else:
            click.echo(f"❌ Authentication failed for account '{account_name}'.")
    else:
        click.echo(f"  To authenticate, run: gtasks --account {account_name} auth")


@account.command(name='remove')
@click.argument('name', required=False)
@click.option('--name', '-n', 'option_name', help='Account name')
def remove(name, option_name):
    """Remove a Google Tasks account configuration"""
    account_name = name or option_name
    if not account_name:
        click.echo("❌ Error: Account name is required.")
        raise click.Abort()

    from gtasks_cli.storage.config_manager import ConfigManager
    config = ConfigManager.get_global_config()
    accounts = config.get('accounts', {})

    if account_name in accounts:
        del accounts[account_name]
        config.set('accounts', accounts)
        click.echo(f"✅ Removed account '{account_name}' from configuration.")
    else:
        click.echo(f"⚠️ Account '{account_name}' was not found in configuration.")