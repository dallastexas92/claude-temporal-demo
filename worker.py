import asyncio
import os
import logging
from dotenv import load_dotenv
from temporalio.client import Client, TLSConfig
from temporalio.worker import Worker

from activities import get_claude_response
from workflows import ClaudeChatWorkflow


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_worker():
    """Run a Temporal worker that hosts the Claude workflow and activities."""
    # Load environment variables
    load_dotenv()
    
    # Get Temporal connection settings
    is_cloud = os.environ.get("TEMPORAL_ADDRESS", "").endswith("tmprl.cloud:7233")
    
    # Connect to Temporal service
    if is_cloud:
        # Connect to Temporal Cloud
        logger.info("Connecting to Temporal Cloud")
        client_cert_path = os.environ.get("TEMPORAL_CLIENT_CERT")
        client_key_path = os.environ.get("TEMPORAL_CLIENT_KEY")
        
        if not client_cert_path or not client_key_path:
            raise ValueError("Temporal Cloud credentials not properly configured")
        
        # Create TLS config for Temporal Cloud
        tls_config = TLSConfig(
            client_cert=open(client_cert_path, "rb").read(),
            client_private_key=open(client_key_path, "rb").read(),
        )
        # Connect to Temporal Cloud
        client = await Client.connect(
            os.environ.get("TEMPORAL_ADDRESS", ""),
            namespace=os.environ.get("TEMPORAL_NAMESPACE", "default"),
            tls=tls_config,
        )
    else:
        # Connect to local Temporal server
        logger.info("Connecting to local Temporal server")
        client = await Client.connect("localhost:7233")
    
    # Run a worker for the "claude-queue" task queue
    logger.info("Starting worker")
    worker = Worker(
        client,
        task_queue="claude-queue",
        workflows=[ClaudeChatWorkflow],
        activities=[get_claude_response],
    )
    
    await worker.run()


if __name__ == "__main__":
    # Run the worker
    asyncio.run(run_worker())