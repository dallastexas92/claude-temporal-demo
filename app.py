import os
import asyncio
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from temporalio.client import Client, TLSConfig
from workflows import ClaudeWorkflow, ClaudePromptInput

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__, static_folder="static")

# Global variables
temporal_client = None


async def get_temporal_client():
    """Get or create the Temporal client."""
    global temporal_client
    
    if temporal_client is not None:
        return temporal_client
    
    # Get Temporal connection settings
    is_cloud = os.environ.get("TEMPORAL_ADDRESS", "").endswith("tmprl.cloud:7233")
    
    # Connect to Temporal service
    if is_cloud:
        # Connect to Temporal Cloud
        app.logger.info("Connecting to Temporal Cloud")
        client_cert_path = os.environ.get("TEMPORAL_CLIENT_CERT")
        client_key_path = os.environ.get("TEMPORAL_CLIENT_KEY")
        
        if not client_cert_path or not client_key_path:
            raise ValueError("Temporal Cloud credentials not properly configured")
        
        # Create TLS config for Temporal Cloud
        tls_config = TLSConfig(
            client_cert=open(client_cert_path, "rb").read(),
            client_private_key=open(client_key_path, "rb").read(),
        )
        
        client = await Client.connect(
            os.environ.get("TEMPORAL_ADDRESS", ""),
            namespace=os.environ.get("TEMPORAL_NAMESPACE", "default"),
            tls=tls_config,
        )
    else:
        # Connect to local Temporal server
        app.logger.info("Connecting to local Temporal server")
        client = await Client.connect("localhost:7233")
    
    temporal_client = client
    return client


@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html")


@app.route("/api/claude", methods=["POST"])
async def call_claude():
    """API endpoint to call Claude via Temporal workflow."""
    try:
        # Get request data
        data = request.json
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400
            
        prompt = data.get("prompt")
        model = data.get("model", "claude-3-7-sonnet-20250219")
        max_tokens = data.get("maxTokens", 1024)
        
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
        
        # Get the Temporal client
        client = await get_temporal_client()
        
        # Prepare the input
        workflow_input = ClaudePromptInput(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens
        )
        
        # Start the workflow
        workflow_id = f"claude-workflow-{int(asyncio.get_event_loop().time() * 1000)}"
        handle = await client.start_workflow(
            ClaudeWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue="claude-queue",
        )
        
        app.logger.info(f"Started workflow with ID: {workflow_id}")
        
        # Wait for the result
        result = await handle.result()
        
        # Return the result
        return jsonify({
            "text": result.text,
            "requestId": result.request_id
        })
    
    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        # Make sure we return valid JSON even in case of error
        return jsonify({"error": str(e)}), 500