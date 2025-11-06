"""Summary command for processing video transcripts into audio summaries."""

from typing import List
from .base import BaseCommand
from src.time_reclamation.core.youtube import get_summary_service


class SummaryCommand(BaseCommand):
    """Command for processing video summaries."""
    
    @property
    def name(self) -> str:
        """Return the command name."""
        return "summary"
    
    @property
    def description(self) -> str:
        """Return the command description."""
        return "Process video transcripts into audio summaries and deliver via notifications"
    
    @property
    def aliases(self) -> List[str]:
        """Return command aliases."""
        return ["sum"]
    
    @property
    def usage(self) -> str:
        """Return command usage string."""
        return """python -m time_reclamation summary <subcommand> [options]
        
        SUBCOMMANDS:
          process [channel_name]    - Process summaries for all or specific channel
          status [channel_name]     - Show summary processing statistics
          retry                     - Retry failed summaries
          cleanup                   - Clean up orphaned audio files
          help                      - Show this help message
        
        OPTIONS:
          --video <url>             - Process specific video by URL
          --limit <n>               - Limit number of videos to process
          --force                   - Force reprocess even if already processed
          --no-scrape               - Skip scraping for new videos before processing
          --max-age <hours>         - Maximum age for cleanup (default: 24)
        
        EXAMPLES:
          python -m time_reclamation summary process
          python -m time_reclamation summary process "TechWizard9000"
          python -m time_reclamation summary process --limit 5
          python -m time_reclamation summary process --no-scrape
          python -m time_reclamation summary process --video "https://youtube.com/watch?v=..."
          python -m time_reclamation summary status
          python -m time_reclamation summary retry
          python -m time_reclamation summary cleanup --max-age 48"""
    
    def execute(self, args: List[str]) -> int:
        """
        Execute the summary command.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            if not args or args[0] in ["--help", "-h", "help"]:
                self.show_help()
                return 0
            
            subcommand = args[0].lower()
            subcommand_args = args[1:] if len(args) > 1 else []
            
            # Route to appropriate subcommand
            if subcommand == "process":
                return self._handle_process(subcommand_args)
            elif subcommand == "status":
                return self._handle_status(subcommand_args)
            elif subcommand == "retry":
                return self._handle_retry(subcommand_args)
            elif subcommand == "cleanup":
                return self._handle_cleanup(subcommand_args)
            else:
                return self.handle_error(f"Unknown subcommand: {subcommand}")
                
        except Exception as e:
            return self.handle_error(f"Summary command failed: {str(e)}")
    
    def _handle_process(self, args: List[str]) -> int:
        """Handle the process subcommand."""
        try:
            summary_service = get_summary_service()
            
            # Parse arguments
            channel_name = None
            video_url = None
            limit = None
            force = False
            scrape_first = True  # Default to scraping first
            
            i = 0
            while i < len(args):
                if args[i] == "--video" and i + 1 < len(args):
                    video_url = args[i + 1]
                    i += 2
                elif args[i] == "--limit" and i + 1 < len(args):
                    try:
                        limit = int(args[i + 1])
                    except ValueError:
                        return self.handle_error("Limit must be a number")
                    i += 2
                elif args[i] == "--force":
                    force = True
                    i += 1
                elif args[i] == "--no-scrape":
                    scrape_first = False
                    i += 1
                elif not args[i].startswith("--"):
                    channel_name = args[i]
                    i += 1
                else:
                    return self.handle_error(f"Unknown option: {args[i]}")
            
            # Process specific video
            if video_url:
                self.logger.info(f"Processing summary for video: {video_url}")
                result = summary_service.process_video_summary(video_url)
                
                if result.get('success'):
                    self.logger.print_header("Video Summary Processed")
                    self.logger.print_bullet(f"Title: {result.get('video_title', 'Unknown')}")
                    self.logger.print_bullet(f"Summary length: {result.get('summary_length', 0)} characters")
                    return self.handle_success("Video summary processed successfully")
                else:
                    error = result.get('error', 'Unknown error')
                    if result.get('skipped'):
                        self.logger.warning(f"Video skipped: {error}")
                        return 0
                    return self.handle_error(f"Failed to process video: {error}")
            
            # Process channel(s)
            self.logger.info(f"Processing summaries for: {channel_name or 'all enabled channels'}")
            if scrape_first:
                self.logger.info("Will scrape for new videos before processing summaries")
            results = summary_service.process_channel_summaries(channel_name, limit, force, scrape_first)
            
            if 'error' in results:
                return self.handle_error(results['error'])
            
            self.logger.print_header("Summary Processing Results")
            self.logger.print_bullet(f"Processed: {results['processed']}")
            self.logger.print_bullet(f"Failed: {results['failed']}")
            self.logger.print_bullet(f"Skipped: {results['skipped']}")
            
            # Show per-channel results
            if results.get('channel_results'):
                self.logger.print_section("PER-CHANNEL RESULTS")
                for channel_result in results['channel_results']:
                    self.logger.print_bullet(
                        f"{channel_result['channel_name']}: "
                        f"{channel_result['processed']} processed, "
                        f"{channel_result['failed']} failed, "
                        f"{channel_result['skipped']} skipped"
                    )
            
            return self.handle_success("Summary processing completed")
            
        except Exception as e:
            return self.handle_error(f"Processing failed: {str(e)}")
    
    def _handle_status(self, args: List[str]) -> int:
        """Handle the status subcommand."""
        try:
            summary_service = get_summary_service()
            
            # Get summary statistics
            stats = summary_service.get_summary_stats()
            
            if not stats:
                return self.handle_error("Failed to get summary statistics")
            
            self.logger.print_header("Summary Processing Statistics")
            self.logger.print_bullet(f"Total videos with transcripts: {stats.get('total_with_transcripts', 0)}")
            self.logger.print_bullet(f"Summaries processed: {stats.get('summary_processed', 0)}")
            self.logger.print_bullet(f"Pending summaries: {stats.get('pending_summaries', 0)}")
            self.logger.print_bullet(f"Failed summaries: {stats.get('summary_errors', 0)}")
            
            return self.handle_success()
            
        except Exception as e:
            return self.handle_error(f"Failed to get status: {str(e)}")
    
    def _handle_retry(self, args: List[str]) -> int:
        """Handle the retry subcommand."""
        try:
            summary_service = get_summary_service()
            
            # Parse arguments
            limit = None
            
            i = 0
            while i < len(args):
                if args[i] == "--limit" and i + 1 < len(args):
                    try:
                        limit = int(args[i + 1])
                    except ValueError:
                        return self.handle_error("Limit must be a number")
                    i += 2
                else:
                    return self.handle_error(f"Unknown option: {args[i]}")
            
            self.logger.info("Retrying failed summaries")
            results = summary_service.retry_failed_summaries(limit)
            
            if 'error' in results:
                return self.handle_error(results['error'])
            
            self.logger.print_header("Retry Results")
            self.logger.print_bullet(f"Processed: {results['processed']}")
            self.logger.print_bullet(f"Failed: {results['failed']}")
            
            return self.handle_success(results.get('message', 'Retry completed'))
            
        except Exception as e:
            return self.handle_error(f"Retry failed: {str(e)}")
    
    def _handle_cleanup(self, args: List[str]) -> int:
        """Handle the cleanup subcommand."""
        try:
            summary_service = get_summary_service()
            
            # Parse arguments
            max_age = 24  # Default 24 hours
            
            i = 0
            while i < len(args):
                if args[i] == "--max-age" and i + 1 < len(args):
                    try:
                        max_age = int(args[i + 1])
                    except ValueError:
                        return self.handle_error("Max age must be a number")
                    i += 2
                else:
                    return self.handle_error(f"Unknown option: {args[i]}")
            
            self.logger.info(f"Cleaning up audio files older than {max_age} hours")
            results = summary_service.cleanup_audio_files(max_age)
            
            if 'error' in results:
                return self.handle_error(results['error'])
            
            self.logger.print_header("Cleanup Results")
            self.logger.print_bullet(f"Removed files: {results['removed_files']}")
            
            return self.handle_success(results.get('message', 'Cleanup completed'))
            
        except Exception as e:
            return self.handle_error(f"Cleanup failed: {str(e)}")