# Temporal Claude interface

Interact with Claude using a Temporal Workflow - each subsequent message is a Temporal signal

## Setup Instructions

### Prerequisites

- [Virtualenv](https://virtualenv.pypa.io/en/latest/installation.html)

### Setting Up the Project

1. **Clone the Repository**

    ```bash
    git clone https://github.com/dallastexas92/claude-temporal-demo
    ```

2. **Create and Activate a Virtual Environment**

    ```bash
    python -m venv env
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install Dependencies**

    ```bash
    pip install temporalio anthropic flask python-dotenv
    ```

4. **Set Up Environment Variables**

    Create a `.env` file in the root directory of the project and add the following variables:

    ```plaintext
    # Anthropic API key
    ANTHROPIC_API_KEY=your_api_key_here

    # Temporal cloud credentials (only needed for cloud deployment)
    TEMPORAL_NAMESPACE=your_namespace
    TEMPORAL_ADDRESS=your_address.tmprl.cloud:7233
    TEMPORAL_CLIENT_CERT=./certs/client.pem
    TEMPORAL_CLIENT_KEY=./certs/client.key

    # Flask settings
    FLASK_APP=app.py
    FLASK_ENV=development
    ```

    Replace the placeholders with your actual values.

5. **Run the Worker in one terminal**

    ```bash
    python worker.py
    ```
    
7. **Start the Flask app in another terminal**

    ```bash
    flask run
    ```
8. **Access the web interface at http://127.0.0.1:5000**

### Project Structure

- workflows.py - Contains the Temporal workflow definitions
- activities.py - Contains the activities that call the Claude API
- worker.py - Worker process that executes workflows and activities
- app.py - Flask server that handles web requests
- templates/ - HTML templates for the web interface

### Notes

- Ensure your Temporal Cloud URL, certificates, and keys are correctly set in the `.env` file.
- The `.gitignore` file is configured to ignore sensitive files like the virtual environment and certificates.
