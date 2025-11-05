"""LLM command implementation."""

from typing import List
from .base import BaseCommand
from src.time_reclamation.infrastructure.llm import get_llm_manager, LLMStatus


class LLMCommand(BaseCommand):
    """Command to interact with LLM providers and generate responses."""
    
    @property
    def name(self) -> str:
        """Return the command name."""
        return "llm"
    
    @property
    def description(self) -> str:
        """Return the command description."""
        return "Generate responses using LLM providers"
    
    @property
    def aliases(self) -> List[str]:
        """Return command aliases."""
        return ["ai", "generate"]
    
    @property
    def usage(self) -> str:
        """Return command usage string."""
        return f"python -m time_reclamation {self.name} [<instance_name>] --prompt 'Your prompt' [--system 'System prompt'] [--list] [--test]"
    
    def execute(self, args: List[str]) -> int:
        """
        Execute the llm command.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success)
        """
        try:
            # Parse arguments
            instance_name = None
            user_prompt = None
            system_prompt = None
            list_only = False
            test_only = False
            test_instance = None
            
            i = 0
            while i < len(args):
                if args[i] == "--prompt" and i + 1 < len(args):
                    user_prompt = args[i + 1]
                    i += 2
                elif args[i] == "--system" and i + 1 < len(args):
                    system_prompt = args[i + 1]
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
            
            # Get LLM manager
            llm_manager = get_llm_manager()
            
            # Display header
            self.logger.print_header("LLM System")
            
            # Show provider status
            self._show_provider_status(llm_manager)
            
            # Handle list only
            if list_only:
                return self.handle_success()
            
            # Handle test only
            if test_only:
                self._test_provider_connections(llm_manager, test_instance)
                return self.handle_success()
            
            # Generate response
            if user_prompt:
                self._generate_response(llm_manager, instance_name, user_prompt, system_prompt)
                return self.handle_success()
            else:
                return self.handle_error("No prompt provided. Use --prompt 'Your prompt' or --help for usage information.")
            
        except Exception as e:
            return self.handle_error(f"Failed to execute LLM command: {str(e)}")
    
    def _show_provider_status(self, llm_manager) -> None:
        """
        Show the status of all LLM provider instances.
        
        Args:
            llm_manager: LLM manager instance
        """
        self.logger.print_section("LLM PROVIDER INSTANCES STATUS")
        
        provider_status = llm_manager.get_provider_status()
        
        if not provider_status:
            self.logger.print_bullet("No LLM provider instances configured")
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
    
    def _test_provider_connections(self, llm_manager, instance_name=None) -> None:
        """
        Test connections to LLM provider instances.
        
        Args:
            llm_manager: LLM manager instance
            instance_name: Specific instance to test (optional, tests all if not provided)
        """
        self.logger.print_section("CONNECTION TESTS")
        
        test_results = llm_manager.test_providers(instance_name)
        
        if not test_results:
            self.logger.print_bullet("No LLM provider instances to test")
            return
        
        for instance_name, result in test_results.items():
            if result.status == LLMStatus.SUCCESS:
                self.logger.print_bullet(f"✓ {instance_name}: {result.response}")
                if result.generation_time:
                    self.logger.print_bullet(f"  Response time: {result.generation_time:.2f}s", indent=4)
            else:
                self.logger.print_bullet(f"✗ {instance_name}: {result.error_details}")
    
    def _generate_response(self, llm_manager, instance_name=None, user_prompt=None, system_prompt=None) -> None:
        """
        Generate a response using the LLM system.
        
        Args:
            llm_manager: LLM manager instance
            instance_name: Specific instance to use (optional)
            user_prompt: User's input prompt
            system_prompt: System prompt (optional)
        """
        self.logger.print_section("GENERATING RESPONSE")
        
        if not llm_manager.is_any_provider_configured():
            self.logger.print_bullet("⚠️  No LLM provider instances are configured")
            self.logger.print_bullet("Configure LLM provider instances in config.yml to generate responses")
            return
        
        # Show what we're doing
        target_name = f"instance '{instance_name}'" if instance_name else "auto-selected instance"
        self.logger.print_bullet(f"Using: {target_name}")
        self.logger.print_bullet(f"Prompt: {user_prompt}")
        if system_prompt:
            self.logger.print_bullet(f"System: {system_prompt}")
        
        # Generate the response
        result = llm_manager.generate_response(user_prompt, instance_name, system_prompt)
        
        if result.status == LLMStatus.SUCCESS:
            self.logger.print_section("RESPONSE")
            self.logger.print_bullet("✓ Response generated successfully")
            if result.generation_time:
                self.logger.print_bullet(f"Generation time: {result.generation_time:.2f}s")
            
            # Print the response with proper formatting
            print("\n" + "="*60)
            print(result.response)
            print("="*60 + "\n")
            
        else:
            self.logger.print_bullet(f"✗ Failed to generate response: {result.error_details}")
    
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
        self.logger.print_bullet("<instance_name>      Specify which LLM provider instance to use")
        self.logger.print_bullet("--prompt <text>      The prompt to send to the LLM (required for generation)")
        self.logger.print_bullet("--system <text>      System prompt to set context/behavior (optional)")
        self.logger.print_bullet("--list               Show LLM provider instances without generating")
        self.logger.print_bullet("--test [instance]    Test LLM provider connections")
        self.logger.print_bullet("--help, -h           Show this help message")
        
        self.logger.print_section("EXAMPLES")
        self.logger.print_bullet("python main.py llm --list")
        self.logger.print_bullet("python main.py llm --test")
        self.logger.print_bullet("python main.py llm --test local_llama")
        self.logger.print_bullet("python main.py llm --prompt 'Explain quantum computing'")
        self.logger.print_bullet("python main.py llm local_llama --prompt 'Write a Python function'")
        self.logger.print_bullet("python main.py llm --system 'You are a code expert' --prompt 'Fix this bug'")
        self.logger.print_bullet("python -m time_reclamation ai --prompt 'What is machine learning?'")
        
        self.logger.print_section("NOTES")
        self.logger.print_bullet("This command generates responses using configured LLM provider instances")
        self.logger.print_bullet("Configure LLM provider instances in config.yml before using")
        self.logger.print_bullet("Without instance name, the first available instance is used")
        self.logger.print_bullet("System prompts help set the AI's behavior and context")
        self.logger.print_bullet("Use aliases 'ai' or 'generate' as shortcuts for 'llm'")