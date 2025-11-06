"""TTS command implementation."""

from typing import List
from .base import BaseCommand
from src.time_reclamation.infrastructure.tts import get_tts_manager, TTSStatus


class TTSCommand(BaseCommand):
    """Command to interact with TTS providers and generate speech."""
    
    @property
    def name(self) -> str:
        """Return the command name."""
        return "tts"
    
    @property
    def description(self) -> str:
        """Return the command description."""
        return "Generate speech from text using TTS providers"
    
    @property
    def aliases(self) -> List[str]:
        """Return command aliases."""
        return ["speak", "voice"]
    
    @property
    def usage(self) -> str:
        """Return command usage string."""
        return f"python -m time_reclamation {self.name} [<instance_name>] --text 'Your text' [--output filename.wav] [--list] [--test]"
    
    def execute(self, args: List[str]) -> int:
        """
        Execute the tts command.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success)
        """
        try:
            # Parse arguments
            instance_name = None
            text = None
            output_filename = None
            list_only = False
            test_only = False
            test_instance = None
            
            i = 0
            while i < len(args):
                if args[i] == "--text" and i + 1 < len(args):
                    text = args[i + 1]
                    i += 2
                elif args[i] == "--output" and i + 1 < len(args):
                    output_filename = args[i + 1]
                    i += 2
                elif args[i] == "--list":
                    list_only = True
                    i += 1
                elif args[i] == "--test":
                    test_only = True
                    # Check if next arg is an instance name
                    if i + 1 < len(args) and not args[i + 1].startswith("--"):
                        test_instance = args[i + 1]
                        i += 2
                    else:
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
            
            # Get TTS manager
            tts_manager = get_tts_manager()
            
            # Display header
            self.logger.print_header("TTS System")
            
            # Show provider status
            self._show_provider_status(tts_manager)
            
            # Handle list only
            if list_only:
                return self.handle_success()
            
            # Handle test only
            if test_only:
                self._test_provider_connections(tts_manager, test_instance)
                return self.handle_success()
            
            # Generate speech
            if text:
                self._generate_speech(tts_manager, instance_name, text, output_filename)
                return self.handle_success()
            else:
                return self.handle_error("No text provided. Use --text 'Your text' or --help for usage information.")
            
        except Exception as e:
            return self.handle_error(f"Failed to execute TTS command: {str(e)}")
    
    def _show_provider_status(self, tts_manager) -> None:
        """
        Show the status of all TTS provider instances.
        
        Args:
            tts_manager: TTS manager instance
        """
        self.logger.print_section("TTS PROVIDER INSTANCES STATUS")
        
        provider_status = tts_manager.get_provider_status()
        
        if not provider_status:
            self.logger.print_bullet("No TTS provider instances configured")
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
    
    def _test_provider_connections(self, tts_manager, instance_name=None) -> None:
        """
        Test connections to TTS provider instances.
        
        Args:
            tts_manager: TTS manager instance
            instance_name: Specific instance to test (optional, tests all if not provided)
        """
        self.logger.print_section("CONNECTION TESTS")
        
        test_results = tts_manager.test_providers(instance_name)
        
        if not test_results:
            self.logger.print_bullet("No TTS provider instances to test")
            return
        
        for instance_name, result in test_results.items():
            if result.status == TTSStatus.SUCCESS:
                response_info = result.provider_response.get('message', 'Connection successful') if result.provider_response else 'Connection successful'
                self.logger.print_bullet(f"✓ {instance_name}: {response_info}")
                if result.generation_time:
                    self.logger.print_bullet(f"  Generation time: {result.generation_time:.2f}s", indent=4)
                if result.audio_duration:
                    self.logger.print_bullet(f"  Test audio duration: {result.audio_duration:.2f}s", indent=4)
            else:
                self.logger.print_bullet(f"✗ {instance_name}: {result.error_details}")
    
    def _generate_speech(self, tts_manager, instance_name=None, text=None, output_filename=None) -> None:
        """
        Generate speech using the TTS system.
        
        Args:
            tts_manager: TTS manager instance
            instance_name: Specific instance to use (optional)
            text: Text to convert to speech
            output_filename: Output filename (optional)
        """
        self.logger.print_section("GENERATING SPEECH")
        
        if not tts_manager.is_any_provider_configured():
            self.logger.print_bullet("⚠️  No TTS provider instances are configured")
            self.logger.print_bullet("Configure TTS provider instances in config.yml to generate speech")
            return
        
        # Show what we're doing
        target_name = f"instance '{instance_name}'" if instance_name else "auto-selected instance"
        self.logger.print_bullet(f"Using: {target_name}")
        self.logger.print_bullet(f"Text: {text[:100]}{'...' if len(text) > 100 else ''}")
        if output_filename:
            self.logger.print_bullet(f"Output: {output_filename}")
        
        # Generate the speech
        result = tts_manager.generate_speech(text, output_filename, instance_name)
        
        if result.status == TTSStatus.SUCCESS:
            self.logger.print_section("RESULT")
            self.logger.print_bullet("✓ Speech generated successfully")
            if result.output_file:
                self.logger.print_bullet(f"Output file: {result.output_file}")
            if result.generation_time:
                self.logger.print_bullet(f"Generation time: {result.generation_time:.2f}s")
            if result.audio_duration:
                self.logger.print_bullet(f"Audio duration: {result.audio_duration:.2f}s")
            
            # Show additional info if available
            if result.provider_response:
                chunks = result.provider_response.get('chunks')
                if chunks:
                    self.logger.print_bullet(f"Audio chunks: {chunks}")
            
        else:
            self.logger.print_bullet(f"✗ Failed to generate speech: {result.error_details}")
    
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
        self.logger.print_bullet("<instance_name>      Specify which TTS provider instance to use")
        self.logger.print_bullet("--text <text>        The text to convert to speech (required for generation)")
        self.logger.print_bullet("--output <filename>  Output filename (optional, auto-generates if not provided)")
        self.logger.print_bullet("--list               Show TTS provider instances without generating")
        self.logger.print_bullet("--test [instance]    Test TTS provider connections")
        self.logger.print_bullet("--help, -h           Show this help message")
        
        self.logger.print_section("EXAMPLES")
        self.logger.print_bullet("python main.py tts --list")
        self.logger.print_bullet("python main.py tts --test")
        self.logger.print_bullet("python main.py tts --test piper_english")
        self.logger.print_bullet("python main.py tts --text 'Hello, world!'")
        self.logger.print_bullet("python main.py tts --text 'Hello, world!' --output greeting.wav")
        self.logger.print_bullet("python main.py tts piper_english --text 'This is a test'")
        self.logger.print_bullet("python -m time_reclamation speak --text 'Using alias command'")
        
        self.logger.print_section("NOTES")
        self.logger.print_bullet("This command generates speech from text using configured TTS provider instances")
        self.logger.print_bullet("Configure TTS provider instances in config.yml before using")
        self.logger.print_bullet("Without instance name, the first available instance is used")
        self.logger.print_bullet("Output files are saved to the configured output directory (default: cache_data/tts)")
        self.logger.print_bullet("Use aliases 'speak' or 'voice' as shortcuts for 'tts'")