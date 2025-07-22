#!/usr/bin/env python3
"""
Route Embedding Generation Script
Generates semantic embeddings for climbing routes for vector similarity search
"""

import os
import sys
import time
import logging
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.database.utils import create_connection
from src.vectordb.embedding_functions import (
    get_routes_for_embedding,
    process_route_for_embedding
)

def setup_database_schema(cursor):
    """Run the database setup SQL if needed"""
    try:
        # Check if vectors schema exists
        cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'vectors'")
        if not cursor.fetchone():
            print("Setting up vectors schema...")
            
            # Read and execute setup SQL
            setup_sql_path = os.path.join(os.path.dirname(__file__), 'setup_embeddings.sql')
            with open(setup_sql_path, 'r') as f:
                setup_sql = f.read()
            
            # Execute each statement separately
            statements = [stmt.strip() for stmt in setup_sql.split(';') if stmt.strip()]
            for statement in statements:
                if statement:
                    cursor.execute(statement)
            
            print("✓ Vectors schema created")
        else:
            print("✓ Vectors schema already exists")
            
    except Exception as e:
        print(f"Error setting up database schema: {e}")
        return False
    
    return True

def log_generation_progress(cursor, route_id, status, error_message=None, tokens_used=None, processing_time_ms=None):
    """Log embedding generation progress (simplified for now)"""
    # Just print for now - can add database logging later
    print(f"Route {route_id}: {status}" + (f" - {error_message}" if error_message else ""))

def setup_logging():
    """Setup logging to both file and console"""
    log_filename = f"embedding_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'logs/{log_filename}'),
            logging.StreamHandler()  # Also print to console
        ]
    )
    return log_filename

def generate_embeddings_batch(batch_size=10, max_routes=None, user_id=None, force_regenerate=False):
    """Generate embeddings for routes in batches"""
    
    log_file = setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Starting embedding generation...")
    logger.info(f"Log file: logs/{log_file}")
    
    if user_id:
        logger.info(f"Focusing on routes for user: {user_id}")
    if force_regenerate:
        logger.info("🔄 FORCE REGENERATE: Will overwrite ALL existing embeddings")
    logger.info(f"Batch size: {batch_size}")
    if max_routes:
        logger.info(f"Max routes: {max_routes}")
    
    total_processed = 0
    total_successful = 0
    total_failed = 0
    start_time = time.time()
    
    with create_connection() as connection:
        cursor = connection.cursor()
        
        # Setup database schema
        if not setup_database_schema(cursor):
            logger.error("❌ Failed to setup database schema")
            return
        
        connection.commit()
        logger.info("✅ Database schema verified")
        
        # Get total count for progress tracking
        if user_id:
            if force_regenerate:
                cursor.execute("SELECT COUNT(DISTINCT r.id) FROM routes.Routes r INNER JOIN routes.Ticks t ON r.id = t.route_id WHERE t.user_id = %s", (user_id,))
            else:
                cursor.execute("""
                    SELECT COUNT(DISTINCT r.id) 
                    FROM routes.Routes r
                    INNER JOIN routes.Ticks t ON r.id = t.route_id
                    LEFT JOIN vectors.route_embeddings re ON r.id = re.route_id AND re.content_type = 'full_route'
                    WHERE t.user_id = %s AND re.id IS NULL
                """, (user_id,))
            total_routes_to_process = cursor.fetchone()[0]
            logger.info(f"📊 Total routes to process: {total_routes_to_process}")
        
        batch_count = 0
        current_offset = 0
        while True:
            # Check if we've hit our limit
            if max_routes and total_processed >= max_routes:
                break
            
            # Get batch of routes
            remaining = max_routes - total_processed if max_routes else batch_size
            current_batch_size = min(batch_size, remaining)
            
            routes = get_routes_for_embedding(cursor, current_batch_size, user_id, force_regenerate, current_offset)
            
            if not routes:
                logger.info("✅ No more routes to process")
                break
            
            batch_count += 1
            logger.info(f"\n📦 Processing batch {batch_count} of {len(routes)} routes...")
            if user_id:
                progress_pct = (total_processed / total_routes_to_process * 100) if total_routes_to_process > 0 else 0
                logger.info(f"📈 Overall progress: {total_processed}/{total_routes_to_process} ({progress_pct:.1f}%)")
            
            batch_successful = 0
            batch_failed = 0
            batch_start_time = time.time()
            
            for i, route in enumerate(routes, 1):
                route_id = route['route_id']
                route_name = route['route_name']
                
                logger.info(f"  [{i}/{len(routes)}] Processing: {route_name}")
                
                route_start_time = time.time()
                
                try:
                    # Log start
                    log_generation_progress(cursor, route_id, 'processing')
                    
                    # Process the route
                    success = process_route_for_embedding(cursor, route)
                    
                    processing_time_ms = int((time.time() - route_start_time) * 1000)
                    
                    if success:
                        log_generation_progress(cursor, route_id, 'completed', processing_time_ms=processing_time_ms)
                        batch_successful += 1
                        logger.info(f"    ✓ Success ({processing_time_ms}ms)")
                    else:
                        log_generation_progress(cursor, route_id, 'failed', error_message="Processing failed")
                        batch_failed += 1
                        logger.warning(f"    ❌ Failed")
                        
                except Exception as e:
                    processing_time_ms = int((time.time() - route_start_time) * 1000)
                    error_msg = str(e)[:500]  # Truncate long error messages
                    log_generation_progress(cursor, route_id, 'failed', error_message=error_msg, processing_time_ms=processing_time_ms)
                    batch_failed += 1
                    logger.error(f"    ❌ Error: {e}")
                
                # Commit after each route to save progress
                connection.commit()
                
                # Small delay to be nice to the API
                time.sleep(0.1)
            
            batch_time = time.time() - batch_start_time
            total_processed += len(routes)
            total_successful += batch_successful
            total_failed += batch_failed
            
            logger.info(f"✅ Batch {batch_count} complete: {batch_successful} successful, {batch_failed} failed ({batch_time:.1f}s)")
            
            # Increment offset for next batch (important for force_regenerate)
            current_offset += len(routes)
            
            # Break if this batch was smaller than requested (no more routes)
            if len(routes) < current_batch_size:
                break
    
    total_time = time.time() - start_time
    logger.info(f"\n🎉 Embedding generation complete!")
    logger.info(f"📊 Final Stats:")
    logger.info(f"  Total processed: {total_processed}")
    logger.info(f"  Successful: {total_successful}")
    logger.info(f"  Failed: {total_failed}")
    logger.info(f"  Success rate: {total_successful/total_processed*100:.1f}%" if total_processed > 0 else "N/A")
    logger.info(f"  Total time: {total_time/60:.1f} minutes")
    logger.info(f"  Average time per route: {total_time/total_processed:.1f}s" if total_processed > 0 else "N/A")

def get_embedding_stats():
    """Show current embedding statistics"""
    with create_connection() as connection:
        cursor = connection.cursor()
        
        # Check if schema exists
        cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'vectors'")
        if not cursor.fetchone():
            print("❌ Vectors schema not found. Run setup first.")
            return
        
        # Get route counts
        cursor.execute("SELECT COUNT(*) FROM routes.Routes")
        total_routes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT route_id) FROM vectors.route_embeddings WHERE content_type = 'full_route'")
        embedded_routes = cursor.fetchone()[0]
        
        # Skip generation log stats for now
        log_stats = {}
        
        print(f"📊 Embedding Statistics:")
        print(f"Total routes: {total_routes:,}")
        print(f"Routes with embeddings: {embedded_routes:,}")
        print(f"Coverage: {embedded_routes/total_routes*100:.1f}%" if total_routes > 0 else "N/A")
        print(f"Remaining: {total_routes - embedded_routes:,}")
        
        if log_stats:
            print(f"\nGeneration Log:")
            for status, count in log_stats.items():
                print(f"  {status}: {count:,}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate route embeddings for semantic search")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of routes to process per batch")
    parser.add_argument("--max-routes", type=int, help="Maximum number of routes to process (for testing)")
    parser.add_argument("--user-id", type=str, help="Focus on routes for a specific user (e.g., 200362278)")
    parser.add_argument("--force-regenerate", action="store_true", help="Regenerate ALL embeddings, even existing ones")
    parser.add_argument("--stats", action="store_true", help="Show embedding statistics")
    parser.add_argument("--setup", action="store_true", help="Setup database schema only")
    
    args = parser.parse_args()
    
    if args.stats:
        get_embedding_stats()
    elif args.setup:
        with create_connection() as connection:
            cursor = connection.cursor()
            if setup_database_schema(cursor):
                connection.commit()
                print("✅ Database schema setup complete")
            else:
                print("❌ Database schema setup failed")
    else:
        generate_embeddings_batch(
            batch_size=args.batch_size,
            max_routes=args.max_routes,
            user_id=args.user_id,
            force_regenerate=args.force_regenerate
        )