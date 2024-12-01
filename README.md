# AI Ecommerce

## Instructions to Run the App

1.  **Clone the repository:**

    ```sh
    git clone <repository-url>
    cd <repository-directory>

    ```

2.  **Create and activate a virtual environment:**
    python -m venv venv
    source venv/bin/activate # On Windows use `venv\Scripts\activate`

3.  **Install the required dependencies:**

    pip install -r requirements.txt

4.  **Set up environment variables:**

    Create a .env file in the root directory of the project.
    Copy the contents of var.env into the .env file and fill in the necessary API keys.

5.  **Run the Streamlit app:**
    streamlit run main.py

6.  **Access the app:**
    Open your web browser and go to http://localhost:8501.

## Fine-tuning the Model

    1. Upload a file for fine-tuning:

        Go to the "Fine-tuning" section in the sidebar.
        Upload a file in one of the supported formats (txt, pdf, csv, xlsx, docx).
    2. Wait for the fine-tuning process to complete:

            The app will process the uploaded file and update the model.
            Once the fine-tuning is done, you can start chatting with the updated RAG Assistant.

## Chat with the AI Ecommerce Chatbot

        Go to the "Chat" section in the sidebar.
        Enter your query in the input box and get responses from the AI Ecommerce Chatbot.
