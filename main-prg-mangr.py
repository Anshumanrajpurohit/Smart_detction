#!/usr/bin/env python3
"""
Face Recognition System - Enhanced Main Program Manager
Orchestrates face detection, storage, and comparison processes with improved timing
"""

import time
import sys
import os
from datetime import datetime
import threading
import signal

# Import our custom modules
from creating_db import create_databases
from detecting_storing import detect_and_store_new_faces, test_camera
from db_face_compare import process_interval, print_database_stats, get_people_list

class FaceRecognitionSystem:
    def __init__(self):
        self.running = False
        self.detection_time = 20     # 20 seconds per detection cycle as requested
        self.cycle_delay = 20        # 20 seconds between cycles as requested
        self.cycle_count = 0
        self.total_faces_detected = 0
        self.successful_cycles = 0
        
    def setup(self):
        """Initialize the system with enhanced checks"""
        print("🚀 Enhanced Face Recognition System Starting...")
        print("="*70)
        
        # Create databases
        print("🏗️ Setting up databases...")
        try:
            create_databases()
            print("✅ Databases initialized successfully")
        except Exception as e:
            print(f"❌ Database setup failed: {e}")
            return False
        
        # Test camera with detailed feedback
        print("🧪 Testing camera system...")
        if not test_camera():
            print("❌ Camera test failed! Please check:")
            print("   • Camera is connected and not used by other applications")
            print("   • Camera permissions are granted")
            print("   • Try different camera indices (0, 1, 2)")
            return False
        
        # Print initial statistics
        print("📊 Current system status:")
        print_database_stats()
        
        print("✅ System setup completed successfully!")
        print(f"🎬 Detection cycle: {self.detection_time} seconds")
        print(f"⏳ Cycle delay: {self.cycle_delay} seconds")
        return True
    
    def run_detection_cycle(self):
        """Run one complete detection and comparison cycle with enhanced feedback"""
        self.cycle_count += 1
        cycle_start = datetime.now()
        
        print(f"\n🔄 CYCLE #{self.cycle_count} STARTING...")
        print(f"⏰ Started at: {cycle_start.strftime('%H:%M:%S')}")
        print(f"🎬 Detection time: {self.detection_time} seconds")
        print("-" * 60)
        
        faces_detected_this_cycle = 0
        cycle_successful = False
        
        try:
            # Step 1: Face Detection and Storage
            print("📸 STEP 1: Face Detection and Storage")
            print(f"👀 Starting {self.detection_time}-second detection window...")
            
            faces_found = detect_and_store_new_faces(
                video_source=0, 
                detection_time=self.detection_time
            )
            
            if faces_found:
                faces_detected_this_cycle = 1  # At least one face was detected
                print("✅ New faces detected and stored successfully")
            else:
                print("ℹ️ No new faces detected in this cycle")
            
            # Step 2: Face Comparison and Processing (ALWAYS run this)
            print(f"\n🔍 STEP 2: Face Comparison and Processing")
            print("🧠 Analyzing faces for duplicates and matches...")
            
            comparison_result = process_interval()
            
            if comparison_result:
                print("✅ Face comparison completed successfully")
                cycle_successful = True
                if faces_found:
                    self.total_faces_detected += 1
            else:
                print("⚠️ Face comparison encountered issues")
            
            # Step 3: Updated Statistics and Summary
            print(f"\n📊 STEP 3: Cycle Summary")
            print_database_stats()
            
            # Show current people summary
            people = get_people_list()
            if people:
                print(f"\n👥 Known People Summary ({len(people)} total):")
                # Show top 5 most active people
                for i, (person_id, name, visits, first_seen, last_seen, quality) in enumerate(people[:5]):
                    quality_str = f"{quality:.2f}" if quality else "N/A"
                    print(f"   {i+1}. {name} (ID:{person_id})")
                    print(f"      📈 Visits: {visits} | Quality: {quality_str} | Last: {last_seen}")
                
                if len(people) > 5:
                    print(f"   ... and {len(people)-5} more people")
                    
                # Calculate total visits
                total_visits = sum(person[2] for person in people)  # visits is index 2
                print(f"\n📊 Total visits across all people: {total_visits}")
            else:
                print("\n👥 No people registered yet")
            
            if cycle_successful:
                self.successful_cycles += 1
                
        except KeyboardInterrupt:
            print("\n🛑 Cycle interrupted by user")
            raise
        except Exception as e:
            print(f"❌ Error in detection cycle: {e}")
            print("🔧 System will continue with next cycle...")
        
        finally:
            cycle_end = datetime.now()
            cycle_duration = (cycle_end - cycle_start).total_seconds()
            
            print(f"\n⏱️ Cycle #{self.cycle_count} completed in {cycle_duration:.1f} seconds")
            if cycle_successful:
                print("✅ Cycle completed successfully")
            else:
                print("⚠️ Cycle completed with issues")
            print("=" * 70)
            
            return cycle_successful
    
    def run_continuous(self):
        """Run the system continuously with enhanced monitoring"""
        if not self.setup():
            print("❌ System setup failed. Exiting...")
            return False
            
        self.running = True
        start_time = datetime.now()
        
        print(f"\n🎬 STARTING CONTINUOUS OPERATION")
        print(f"🎥 Detection window: {self.detection_time} seconds per cycle")
        print(f"⏳ Rest period: {self.cycle_delay} seconds between cycles")
        print("🛑 Press Ctrl+C to stop gracefully")
        print("=" * 70)
        
        try:
            while self.running:
                cycle_success = self.run_detection_cycle()
                
                if self.running:  # Check if still running after cycle
                    print(f"😴 Resting for {self.cycle_delay} seconds before next cycle...")
                    print("💡 During this time, the system processes and organizes detected faces")
                    
                    # Use smaller sleep intervals to allow for graceful shutdown
                    for i in range(self.cycle_delay):
                        if not self.running:
                            break
                        time.sleep(1)
                        
                        # Show countdown every 5 seconds
                        remaining = self.cycle_delay - i - 1
                        if remaining > 0 and remaining % 5 == 0:
                            print(f"⏳ {remaining} seconds until next cycle...")
                    
        except KeyboardInterrupt:
            print(f"\n🛑 System gracefully stopped by user")
        except Exception as e:
            print(f"\n❌ System error: {e}")
            print("🔧 Check logs and system configuration")
        finally:
            self.running = False
            self.print_final_summary(start_time)
            
        return True
    
    def print_final_summary(self, start_time):
        """Print comprehensive final summary"""
        total_time = (datetime.now() - start_time).total_seconds()
        
        print(f"\n📊 FINAL SYSTEM SUMMARY")
        print("=" * 50)
        print(f"⏱️ Total runtime: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        print(f"🔄 Total cycles completed: {self.cycle_count}")
        print(f"✅ Successful cycles: {self.successful_cycles}")
        print(f"📸 Cycles with new faces: {self.total_faces_detected}")
        
        if self.cycle_count > 0:
            success_rate = (self.successful_cycles / self.cycle_count) * 100
            print(f"📈 Success rate: {success_rate:.1f}%")
            avg_cycle_time = total_time / self.cycle_count
            print(f"⚡ Average cycle time: {avg_cycle_time:.1f} seconds")
        
        # Show final database state
        print(f"\n📊 Final Database State:")
        print_database_stats()
        
        people = get_people_list()
        if people:
            total_visits = sum(person[2] for person in people)
            print(f"\n🎯 Final Results:")
            print(f"   👥 Total people registered: {len(people)}")
            print(f"   📈 Total visits recorded: {total_visits}")
            print(f"   🏆 Most active person: {people[0][1]} ({people[0][2]} visits)")
        
        print("\n👋 Face Recognition System Stopped")
                # Additional summary for total visitors and revisitors
        if people:
            total_people = len(people)
            revisitors = sum(1 for person in people if person[2] > 1)  # person[2] = visits
            print(f"\n📈 Visitor Summary:")
            print(f"   👤 Total unique visitors: {total_people}")
            print(f"   🔁 Total revisitors (visited more than once): {revisitors}")

        print("💾 All data has been saved to databases")
    
    def run_single_cycle(self):
        """Run just one detection and comparison cycle"""
        if not self.setup():
            return False
            
        print(f"\n🎯 RUNNING SINGLE CYCLE MODE")
        print(f"🎬 Detection window: {self.detection_time} seconds")
        print("=" * 70)
        
        try:
            success = self.run_detection_cycle()
            if success:
                print("✅ Single cycle completed successfully")
                return True
            else:
                print("⚠️ Single cycle completed with issues")
                return False
        except Exception as e:
            print(f"❌ Single cycle failed: {e}")
            return False
    
    def stop(self):
        """Stop the system gracefully"""
        print("\n🛑 Initiating graceful shutdown...")
        self.running = False

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print(f"\n🛑 Received interrupt signal ({signum})")
    print("💾 Saving data and shutting down gracefully...")
    sys.exit(0)

def print_help():
    """Print detailed help information"""
    print("🔧 FACE RECOGNITION SYSTEM - USAGE GUIDE")
    print("=" * 60)
    print("📋 Available Commands:")
    print("   python main-prg-mangr.py                - Run continuously (default)")
    print("   python main-prg-mangr.py single         - Run single 20-second cycle")
    print("   python main-prg-mangr.py setup          - Setup databases only")
    print("   python main-prg-mangr.py stats          - Show current statistics")
    print("   python main-prg-mangr.py help           - Show this detailed help")
    print()
    print("🎬 System Configuration:")
    print("   • Detection window: 20 seconds per cycle")
    print("   • Rest period: 20 seconds between cycles")
    print("   • Face comparison: Advanced similarity detection")
    print("   • Storage: SQLite databases with quality scoring")
    print()
    print("🧠 How It Works:")
    print("   1. Detects faces using camera for 20 seconds")
    print("   2. Compares new faces with existing database")
    print("   3. Removes exact duplicates automatically")
    print("   4. Increases visit count for similar faces")
    print("   5. Adds completely new faces as new people")
    print("   6. Waits 20 seconds before next cycle")
    print()
    print("💡 Tips:")
    print("   • Ensure good lighting for better face detection")
    print("   • Face the camera directly for best results")
    print("   • System automatically handles duplicates")
    print("   • Use Ctrl+C to stop gracefully")

def main():
    """Enhanced main entry point with better argument handling"""
    # Set up signal handling for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create system instance
    system = FaceRecognitionSystem()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        print(f"🎯 Running in {mode.upper()} mode")
        print("=" * 50)
        
        if mode == 'single':
            print("🔄 Single cycle mode - one detection and comparison cycle")
            success = system.run_single_cycle()
            sys.exit(0 if success else 1)
            
        elif mode == 'setup':
            print("🏗️ Setup mode - initializing databases and testing camera")
            success = system.setup()
            if success:
                print("✅ Setup completed successfully")
                print("💡 You can now run the system with: python main-prg-mangr.py")
            sys.exit(0 if success else 1)
            
        elif mode == 'stats':
            print("📊 Statistics mode - showing current database state")
            try:
                create_databases()  # Ensure databases exist
                print_database_stats()
                
                people = get_people_list()
                if people:
                    print(f"\n👥 Detailed People List:")
                    for person_id, name, visits, first_seen, last_seen, quality in people:
                        quality_str = f"{quality:.2f}" if quality else "N/A"
                        print(f"\n   📋 Person ID {person_id}: {name}")
                        print(f"      📈 Total Visits: {visits}")
                        print(f"      🌟 Quality Score: {quality_str}")
                        print(f"      📅 First Seen: {first_seen}")
                        print(f"      🕐 Last Seen: {last_seen}")
                        
                    total_visits = sum(person[2] for person in people)
                    avg_quality = sum(person[5] for person in people if person[5]) / len([p for p in people if p[5]])
                    
                    print(f"\n📊 Summary Statistics:")
                    print(f"   👥 Total People: {len(people)}")
                    print(f"   📈 Total Visits: {total_visits}")
                    print(f"   🌟 Average Quality: {avg_quality:.2f}")
                else:
                    print("\n👥 No people found in database")
                    
            except Exception as e:
                print(f"❌ Error showing stats: {e}")
            sys.exit(0)
            
        elif mode == 'help':
            print_help()
            sys.exit(0)
            
        elif mode == 'cleanup':
            print("🧹 Cleanup mode - removing duplicate faces and optimizing database")
            try:
                create_databases()
                from db_face_compare import cleanup_duplicates
                cleanup_duplicates()
                print("✅ Database cleanup completed")
            except Exception as e:
                print(f"❌ Cleanup failed: {e}")
            sys.exit(0)
            
        elif mode == 'test':
            print("🧪 Test mode - testing all system components")
            try:
                # Test database creation
                print("Testing database creation...")
                create_databases()
                print("✅ Database test passed")
                
                # Test camera
                print("Testing camera...")
                if test_camera():
                    print("✅ Camera test passed")
                else:
                    print("❌ Camera test failed")
                    
                # Test face comparison
                print("Testing face comparison system...")
                comparison_result = process_interval()
                if comparison_result is not None:
                    print("✅ Face comparison test passed")
                else:
                    print("❌ Face comparison test failed")
                    
                print("🎉 All tests completed")
                
            except Exception as e:
                print(f"❌ Test failed: {e}")
            sys.exit(0)
            
        else:
            print(f"❌ Unknown mode: {mode}")
            print("💡 Use 'help' to see available commands")
            sys.exit(1)
    
    # Default mode: continuous operation
    print("🎬 Starting continuous face recognition system...")
    print("💡 Use Ctrl+C to stop gracefully")
    print("🔧 Use 'python main-prg-mangr.py help' for more options")
    
    try:
        success = system.run_continuous()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 System stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ System error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()