import streamlit as st
import os
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts.prompt import PromptTemplate
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory
from langchain_community.document_loaders import Docx2txtLoader, UnstructuredExcelLoader, CSVLoader, TextLoader, PyPDFLoader
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from fpdf import FPDF

from prompt import prompt_template_text


class Main:
    def __init__(self):
        self.load_env_variables()
        self.setup_prompt_template()
        self.retriever = None
        self.relative_path = 'data'
        self.filename = 'dummy.txt'
        self.absolute_path = os.path.join(self.relative_path, self.filename)
        self.initialize_retriever(self.absolute_path)
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

    def load_env_variables(self):
        load_dotenv('var.env')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")

    def setup_prompt_template(self):
        self.prompt_template = PromptTemplate(
            input_variables=["history", "context", "question"],
            template=prompt_template_text,
        )

    def initialize_retriever(self, directory_path):
        loader = TextLoader(directory_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=10000, chunk_overlap=200)
        docs = text_splitter.split_documents(documents)
        embeddings = OpenAIEmbeddings()
        Pinecone(api_key=self.pinecone_api_key, environment='gcp-starter')
        vectbd = PineconeVectorStore.from_documents(
            docs, embeddings, index_name=self.pinecone_index_name)
        self.retriever = vectbd.as_retriever()

    def finetune(self, file_path):
        if file_path.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif file_path.endswith('.txt'):
            loader = TextLoader(file_path)
        elif file_path.endswith('.csv'):
            loader = CSVLoader(file_path=file_path)
        elif file_path.endswith('.xlsx'):
            loader = UnstructuredExcelLoader(file_path, mode="elements")
        elif file_path.endswith('.docx'):
            loader = Docx2txtLoader(file_path)
        else:
            raise ValueError("Unsupported file type.")

        documents = loader.load_and_split() if hasattr(
            loader, 'load_and_split') else loader.load()

        self.process_documents(documents)

        # Remove the file after fine-tuning
        if os.path.exists(file_path):
            os.remove(file_path)

    def process_documents(self, documents):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=10000, chunk_overlap=200)
        docs = text_splitter.split_documents(documents)
        embeddings = OpenAIEmbeddings()
        Pinecone(api_key=self.pinecone_api_key, environment='gcp-starter')
        vectbd = PineconeVectorStore.from_documents(
            docs, embeddings, index_name=self.pinecone_index_name)
        self.retriever = vectbd.as_retriever()

    def chat(self, user_input):
        chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type='stuff',
            retriever=self.retriever,
            chain_type_kwargs={"verbose": False, "prompt": self.prompt_template,
                               "memory": ConversationBufferMemory(memory_key="history", input_key="question")}
        )
        assistant_response = chain.invoke(user_input)
        response_text = assistant_response['result']

        return response_text

    def generate_quiz(self, subject, num_questions, instruction):
        chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type='stuff',
            retriever=self.retriever,
            chain_type_kwargs={"verbose": False, "prompt": self.prompt_template,
                               "memory": ConversationBufferMemory(memory_key="history", input_key="question")}
        )

        prompt = f"Generate a quiz with {num_questions} MCQs for {subject}. {instruction} Make sure to mark the correct answer with [Correct]."
        assistant_response = chain.invoke(prompt)
        return assistant_response['result']

    def generate_pdf(self, quiz, user_answers, correct_answers):
        pdf = FPDF()
        pdf.add_page()
        relative_font_path = "font_path"
        filename_font_path = "arial-unicode-ms.ttf"
        font_path = os.path.join(relative_font_path, filename_font_path)
        # font_path = "/path/to/arial-unicode-ms.ttf"  # Update this path
        pdf.add_font("ArialUnicode", "", font_path, uni=True)
        pdf.set_font("ArialUnicode", size=12)
        pdf.cell(200, 10, txt="AI-QuizCraft", ln=True, align='C')
        pdf.cell(200, 10, txt="Quiz Results", ln=True, align='C')

        for i, qa in enumerate(quiz):
            question = qa["question"]
            options = qa["options"]
            user_answer = user_answers[i]
            correct_answer = correct_answers[i]

            pdf.cell(200, 10, txt=f"Question {i+1}: {question}", ln=True)
            for option in options:
                pdf.cell(200, 10, txt=option, ln=True)
            pdf.cell(
                200, 10, txt=f"(Your Answer: {user_answer}). Correct Answer: {correct_answer}", ln=True)
            pdf.cell(200, 10, txt="", ln=True)  # Add a blank line for spacing

        pdf_output = "quiz_results.pdf"
        pdf.output(pdf_output)
        return pdf_output


main = Main()

st.set_page_config(page_title="AI-QuizCraft", layout="wide")

st.title("AI-QuizCraft")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "quiz" not in st.session_state:
    st.session_state.quiz = []
if "answers" not in st.session_state:
    st.session_state.answers = []
if "correct_answers" not in st.session_state:
    st.session_state.correct_answers = []

option = st.sidebar.selectbox(
    "Choose an option", ("Chat", "Fine-tuning", "Generate Quiz"))

if option == "Chat":
    st.header("Chat with your Docs")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("What is up?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        response = main.chat(prompt)
        st.session_state.messages.append(
            {"role": "assistant", "content": response})

        with st.chat_message("assistant"):
            st.markdown(response)

elif option == "Fine-tuning":
    st.header("Upload your data here")
    uploaded_file = st.file_uploader(
        "Upload a file for fine-tuning", type=["txt", "pdf", "csv", "xlsx", "docx"])

    if uploaded_file is not None:
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        with st.spinner("Fine-tuning in progress..."):
            main.finetune(file_path)
        st.success(
            "Fine-tuning done successfully. You can now chat with the updated RAG Assistant.")

elif option == "Generate Quiz":
    st.header("Generate Quiz")
    subject = st.text_input("Enter the subject (e.g., math, physics, english)")
    num_questions = st.number_input(
        "Number of questions (Max 50)", min_value=1, max_value=50, step=1)  # Set practical limit from 1 to 50
    instruction = st.text_input(
        "Enter any additional instructions (e.g., I need these MCQs from algebra chapter 1)")

    if st.button("Generate Quiz"):
        if subject and num_questions and instruction:
            with st.spinner("Generating quiz..."):
                quiz_text = main.generate_quiz(
                    subject, num_questions, instruction)

                # Process the quiz text to create questions and options
                st.session_state.quiz = []
                st.session_state.correct_answers = []
                lines = quiz_text.strip().split("\n")
                current_question = ""
                current_options = []
                current_answer = None

                for line in lines:
                    if line.startswith("A. ") or line.startswith("B. ") or line.startswith("C. ") or line.startswith("D. "):
                        if "[Correct]" in line:  # Assuming correct option is marked with [Correct]
                            current_answer = line.split(" ")[0].strip()
                            line = line.replace("[Correct]", "").strip()
                        current_options.append(line)
                    else:
                        if current_question and current_options:
                            st.session_state.quiz.append({
                                "question": current_question,
                                "options": current_options
                            })
                            st.session_state.correct_answers.append(
                                current_answer)
                            current_question = line
                            current_options = []
                        else:
                            current_question = line

                if current_question and current_options:
                    st.session_state.quiz.append({
                        "question": current_question,
                        "options": current_options
                    })
                    st.session_state.correct_answers.append(current_answer)

                st.session_state.answers = [None] * len(st.session_state.quiz)

            st.success("Quiz generated successfully!")

    if st.session_state.quiz:
        st.markdown("### Attempt the Quiz")
        for i, qa in enumerate(st.session_state.quiz):
            question = qa["question"]
            options = qa["options"]
            st.markdown(f"**{i+1}. {question}**")
            user_choice = st.radio(
                f"Select an option for question {i+1}", options, key=f"answer_{i}")

            if user_choice:
                st.session_state.answers[i] = user_choice.split(".")[0]

        if st.button("Submit Quiz"):
            user_answers = st.session_state.answers
            for i in range(len(st.session_state.quiz)):
                correct_answer = st.session_state.correct_answers[i]
                selected_answer = st.session_state.answers[i]
                st.write(
                    f"Question {i+1}: (Your Answer: {selected_answer}). Correct Answer: {correct_answer}")

            # Generate PDF
            pdf_file = main.generate_pdf(
                st.session_state.quiz, user_answers, st.session_state.correct_answers)
            with open(pdf_file, "rb") as file:
                st.download_button(
                    label="Download PDF",
                    data=file,
                    file_name="quiz_results.pdf",
                    mime="application/pdf"
                )
