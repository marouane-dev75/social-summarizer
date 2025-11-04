"""Notification test command implementation."""

from typing import List
from .base import BaseCommand
from src.time_reclamation.infrastructure.notifications import get_notification_manager, ProviderType, NotificationStatus


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
        return f"python -m time_reclamation {self.name} [--provider telegram] [--message 'Custom message']"
    
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
            provider_type = None
            custom_message = None
            
            i = 0
            while i < len(args):
                if args[i] == "--provider" and i + 1 < len(args):
                    provider_name = args[i + 1].lower()
                    if provider_name == "telegram":
                        provider_type = ProviderType.TELEGRAM
                    else:
                        return self.handle_error(f"Unknown provider: {provider_name}")
                    i += 2
                elif args[i] == "--message" and i + 1 < len(args):
                    custom_message = args[i + 1]
                    i += 2
                elif args[i] in ["--help", "-h"]:
                    self.show_help()
                    return 0
                else:
                    return self.handle_error(f"Unknown argument: {args[i]}")
            
            # Get notification manager
            notification_manager = get_notification_manager()
            
            # Display header
            self.logger.print_header("Notification System Test")
            
            # Show provider status
            self._show_provider_status(notification_manager)
            
            # Test connections
            self._test_provider_connections(notification_manager)
            
            # Send test message if any provider is configured
            if notification_manager.is_any_provider_configured():
                self._send_test_message(notification_manager, provider_type, custom_message)
            else:
                self.logger.print_section("TEST MESSAGE")
                self.logger.print_bullet("⚠️  No providers are configured - skipping test message")
                self.logger.print_bullet("Configure a provider in config.yml to send test messages")
            
            return self.handle_success()
            
        except Exception as e:
            return self.handle_error(f"Failed to test notifications: {str(e)}")
    
    def _show_provider_status(self, notification_manager) -> None:
        """
        Show the status of all notification providers.
        
        Args:
            notification_manager: Notification manager instance
        """
        self.logger.print_section("PROVIDER STATUS")
        
        provider_status = notification_manager.get_provider_status()
        
        for provider_name, status in provider_status.items():
            name = status['name']
            configured = status['configured']
            available = status['available']
            
            if configured and available:
                self.logger.print_bullet(f"✓ {name}: Configured and available")
            elif configured:
                self.logger.print_bullet(f"⚠️  {name}: Configured but not available")
            else:
                self.logger.print_bullet(f"✗ {name}: Not configured")
    
    def _test_provider_connections(self, notification_manager) -> None:
        """
        Test connections to all configured providers.
        
        Args:
            notification_manager: Notification manager instance
        """
        self.logger.print_section("CONNECTION TESTS")
        
        test_results = notification_manager.test_providers()
        
        for provider_name, result in test_results.items():
            if result.status == NotificationStatus.SUCCESS:
                self.logger.print_bullet(f"✓ {provider_name.title()}: {result.message}")
            else:
                self.logger.print_bullet(f"✗ {provider_name.title()}: {result.error_details}")
    
    def _send_test_message(self, notification_manager, provider_type=None, custom_message=None) -> None:
        """
        Send a test message using the notification system.
        
        Args:
            notification_manager: Notification manager instance
            provider_type: Specific provider to use (optional)
            custom_message: Custom message to send (optional)
        """
        self.logger.print_section("TEST MESSAGE")
        
        # Prepare test message
        if custom_message:
            message = custom_message
        else:
            message = "🚀 Test message from Time Reclamation App!\n\nThis is a test to verify that notifications are working correctly."
        
        # Send the message
        result = notification_manager.send_message(message, provider_type)
        
        if result.status == NotificationStatus.SUCCESS:
            provider_name = "auto-selected provider" if provider_type is None else provider_type.value
            self.logger.print_bullet(f"✓ Test message sent successfully via {provider_name}")
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
        self.logger.print_bullet("--provider <name>    Specify which provider to use for test message")
        self.logger.print_bullet("--message <text>     Send a custom test message")
        self.logger.print_bullet("--help, -h           Show this help message")
        
        self.logger.print_section("EXAMPLES")
        self.logger.print_bullet("python main.py notify-test")
        self.logger.print_bullet("python main.py notify-test --provider telegram")
        self.logger.print_bullet("python main.py notify-test --message 'Hello from TimeReclamation!'")
        self.logger.print_bullet("python -m time_reclamation notification-test --provider telegram")
        
        self.logger.print_section("NOTES")
        self.logger.print_bullet("This command tests all configured notification providers")
        self.logger.print_bullet("Configure providers in config.yml before running tests")
        self.logger.print_bullet("Available providers: telegram")