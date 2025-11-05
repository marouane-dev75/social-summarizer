"""Notification test command implementation."""

from typing import List
from .base import BaseCommand
from src.time_reclamation.infrastructure.notifications import get_notification_manager, NotificationStatus


class NotifyTestCommand(BaseCommand):
    """Command to test notification providers and send test messages."""
    
    @property
    def name(self) -> str:
        """Return the command name."""
        return "notify-test"
    
    @property
    def description(self) -> str:
        """Return the command description."""
        return "Test notification providers and send test messages"
    
    @property
    def aliases(self) -> List[str]:
        """Return command aliases."""
        return ["notification-test", "test-notifications"]
    
    @property
    def usage(self) -> str:
        """Return command usage string."""
        return f"python -m time_reclamation {self.name} [<instance_name>] [--message 'Custom message'] [--list]"
    
    def execute(self, args: List[str]) -> int:
        """
        Execute the notify-test command.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success)
        """
        try:
            # Parse arguments
            instance_name = None
            custom_message = None
            list_only = False
            
            i = 0
            while i < len(args):
                if args[i] == "--message" and i + 1 < len(args):
                    custom_message = args[i + 1]
                    i += 2
                elif args[i] == "--list":
                    list_only = True
                    i += 1
                elif args[i] in ["--help", "-h"]:
                    self.show_help()
                    return 0
                elif not args[i].startswith("--"):
                    # First non-flag argument is the instance name
                    if instance_name is None:
                        instance_name = args[i]
                        i += 1
                    else:
                        return self.handle_error(f"Unexpected argument: {args[i]}")
                else:
                    return self.handle_error(f"Unknown argument: {args[i]}")
            
            # Get notification manager
            notification_manager = get_notification_manager()
            
            # Display header
            self.logger.print_header("Notification System Test")
            
            # Show provider status
            self._show_provider_status(notification_manager)
            
            # If list only, skip testing
            if list_only:
                return self.handle_success()
            
            # Test connections
            self._test_provider_connections(notification_manager, instance_name)
            
            # Send test message if any provider is configured
            if notification_manager.is_any_provider_configured():
                self._send_test_message(notification_manager, instance_name, custom_message)
            else:
                self.logger.print_section("TEST MESSAGE")
                self.logger.print_bullet("⚠️  No provider instances are configured - skipping test message")
                self.logger.print_bullet("Configure provider instances in config.yml to send test messages")
            
            return self.handle_success()
            
        except Exception as e:
            return self.handle_error(f"Failed to test notifications: {str(e)}")
    
    def _show_provider_status(self, notification_manager) -> None:
        """
        Show the status of all notification provider instances.
        
        Args:
            notification_manager: Notification manager instance
        """
        self.logger.print_section("PROVIDER INSTANCES STATUS")
        
        provider_status = notification_manager.get_provider_status()
        
        if not provider_status:
            self.logger.print_bullet("No provider instances configured")
            return
        
        for instance_name, status in provider_status.items():
            name = status['name']
            provider_type = status['type']
            configured = status['configured']
            available = status['available']
            
            if configured and available:
                self.logger.print_bullet(f"✓ {instance_name} ({provider_type}): {name} - Configured and available")
            elif configured:
                self.logger.print_bullet(f"⚠️  {instance_name} ({provider_type}): {name} - Configured but not available")
            else:
                self.logger.print_bullet(f"✗ {instance_name} ({provider_type}): {name} - Not configured")
    
    def _test_provider_connections(self, notification_manager, instance_name=None) -> None:
        """
        Test connections to provider instances.
        
        Args:
            notification_manager: Notification manager instance
            instance_name: Specific instance to test (optional, tests all if not provided)
        """
        self.logger.print_section("CONNECTION TESTS")
        
        test_results = notification_manager.test_providers(instance_name)
        
        if not test_results:
            self.logger.print_bullet("No provider instances to test")
            return
        
        for instance_name, result in test_results.items():
            if result.status == NotificationStatus.SUCCESS:
                self.logger.print_bullet(f"✓ {instance_name}: {result.message}")
            else:
                self.logger.print_bullet(f"✗ {instance_name}: {result.error_details}")
    
    def _send_test_message(self, notification_manager, instance_name=None, custom_message=None) -> None:
        """
        Send a test message using the notification system.
        
        Args:
            notification_manager: Notification manager instance
            instance_name: Specific instance to use (optional)
            custom_message: Custom message to send (optional)
        """
        self.logger.print_section("TEST MESSAGE")
        
        # Prepare test message
        if custom_message:
            message = custom_message
        else:
            message = "🚀 Test message from Time Reclamation App!\n\nThis is a test to verify that notifications are working correctly."
        
        # Send the message
        result = notification_manager.send_message(message, instance_name)
        
        if result.status == NotificationStatus.SUCCESS:
            target_name = "auto-selected instance" if instance_name is None else f"instance '{instance_name}'"
            self.logger.print_bullet(f"✓ Test message sent successfully via {target_name}")
            if result.message:
                self.logger.print_bullet(f"Response: {result.message}")
        else:
            self.logger.print_bullet(f"✗ Failed to send test message: {result.error_details}")
    
    def validate_args(self, args: List[str]) -> bool:
        """
        Validate command arguments.
        
        Args:
            args: Command line arguments
            
        Returns:
            True if arguments are valid
        """
        # Basic validation - detailed parsing is done in execute()
        return True
    
    def show_help(self) -> None:
        """Show help information for this command."""
        super().show_help()
        
        self.logger.print_section("OPTIONS")
        self.logger.print_bullet("<instance_name>      Specify which provider instance to test")
        self.logger.print_bullet("--message <text>     Send a custom test message")
        self.logger.print_bullet("--list               Show provider instances without testing")
        self.logger.print_bullet("--help, -h           Show this help message")
        
        self.logger.print_section("EXAMPLES")
        self.logger.print_bullet("python main.py notify-test")
        self.logger.print_bullet("python main.py notify-test work_bot")
        self.logger.print_bullet("python main.py notify-test personal_bot --message 'Hello from TimeReclamation!'")
        self.logger.print_bullet("python main.py notify-test --list")
        self.logger.print_bullet("python -m time_reclamation notification-test work_bot")
        
        self.logger.print_section("NOTES")
        self.logger.print_bullet("This command tests configured notification provider instances")
        self.logger.print_bullet("Configure provider instances in config.yml before running tests")
        self.logger.print_bullet("Without instance name, all instances are tested")
        self.logger.print_bullet("With instance name, only that instance is tested")