import streamlit as st
from streamlit_mic_recorder import mic_recorder
import whisper
import tempfile
from openai import OpenAI
import os
import json
import warnings
from pydub import AudioSegment
import time
import video_making
import fitz  # PyMuPDF
import re


# 하단 고정 텍스트와 스타일 조정
st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {
        width: 150px !important; # Set the width to your desired value
    }
    </style>
    </div>
    """,
    unsafe_allow_html=True
)


# Suppress FP16 warning
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

# Load the Whisper model
@st.cache_resource
def load_whisper_model():
    return whisper.load_model("small")

model = load_whisper_model()
api_key = os.getenv('OPENAI_API_KEY')  # 환경 변수에서 API 키를 가져옵니다.
client = OpenAI(api_key=api_key)
if not api_key:
    raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_or_create_config(client):
    """config.json에서 ID 읽기. 없으면 OpenAI API로 생성 후 저장. rerun 시 호출 안 됨."""
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)

    changed = False

    if "vector_store_id" not in config:
        vs = client.vector_stores.create(name="ScriptMaker VectorStore")
        config["vector_store_id"] = vs.id
        changed = True

    if "thread_id" not in config:
        thread = client.beta.threads.create()
        config["thread_id"] = thread.id
        changed = True

    if "assistant_id" not in config:
        assistant = client.beta.assistants.create(
            name="ScriptMaker Assistant",
            model="gpt-4o",
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [config["vector_store_id"]]}},
        )
        config["assistant_id"] = assistant.id
        changed = True

    if changed:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

    return config

# 벡터 스토어의 모든 파일을 삭제하는 함수
def delete_all_files_in_vector(vector_store_id, file_list):
    for file in file_list:
        file_id = file.id
        response = client.vector_stores.files.delete(vector_store_id=vector_store_id, file_id=file_id)

# openai에 업로드 된 모든 파일 삭제
def delete_all_files():
    # Get the list of all files
    files = client.files.list()
    
    # Iterate over the files and delete each one
    for file in files:
        file_id = file.id
        client.files.delete(file_id)

def delete_messages(id):
# 스레드의 메시지 목록을 불러오기
    messages = client.beta.threads.messages.list(thread_id=id)
    try:
        # 메시지 목록에서 모든 메시지 삭제하기
        for message in messages:
            message_id = message.id
            client.beta.threads.messages.delete(thread_id=id, message_id=message_id)
    except Exception:
        pass




# Initialize openai assistant - 세션당 1회만 실행 (rerun 시 건너뜀)
if 'vector_store_id' not in st.session_state:
    _config = load_or_create_config(client)
    st.session_state.vector_store_id = _config["vector_store_id"]
    st.session_state.thread_id = _config["thread_id"]
    st.session_state.assistant_id = _config["assistant_id"]
    vector_store_files = client.vector_stores.files.list(vector_store_id=st.session_state.vector_store_id)
    delete_all_files_in_vector(st.session_state.vector_store_id, vector_store_files)
    delete_all_files()

if 'uploader' not in st.session_state:
    st.session_state.uploader = False

if 'uploader_list' not in st.session_state:
    st.session_state.uploader_list = []

if 'ppt' not in st.session_state:
    st.session_state.ppt = False

if "pages" not in st.session_state:
    st.session_state.pages = []  # PDF 페이지 이미지 저장 리스트

if "ppt_texts" not in st.session_state:
    st.session_state.ppt_texts = []  # 텍스트 저장 리스트

if "choose_tp" not in st.session_state:
    st.session_state.choose_tp = "현재 배경"

  

def state_uploader():
    st.session_state.uploader = True

def state_ppt():
    st.session_state.ppt = True
    

# Initialize session state lists
if 'transcriptions' not in st.session_state:
    st.session_state.transcriptions = []
if 'file_paths' not in st.session_state:
    st.session_state.file_paths = []
if 'ts_texts' not in st.session_state:
    st.session_state.ts_texts = []
if 'tts_audio_data' not in st.session_state:
    st.session_state.tts_audio_data = []
if 'tsts_texts' not in st.session_state:
    st.session_state.tsts_texts = []

if 'is_recording' not in st.session_state:
    st.session_state.is_recording = False


if 'temp_page' not in st.session_state:
    st.session_state.temp_page = 0

if 'is_re_recording' not in st.session_state:
    st.session_state.is_re_recording = False

if 'after_script' not in st.session_state:
    st.session_state.after_script = ""

if 'progress_done' not in st.session_state:
    st.session_state.progress_done = False

if 'translated_all_lag' not in st.session_state:
    st.session_state.translated_all_lag = None

if 'user_picture' not in st.session_state:
    st.session_state.user_picture = None
if 'img_save_path' not in st.session_state:
    st.session_state.img_save_path = None

if 'audio_path_os' not in st.session_state:
    st.session_state.audio_path_os = []
if 'result_filename_os' not in st.session_state:
    st.session_state.result_filename_os = []
if 'audio_path_ts' not in st.session_state:
    st.session_state.audio_path_ts = []
if 'result_filename_ts' not in st.session_state:
    st.session_state.result_filename_ts = []




def users_pic():
    st.session_state.user_picture = True




def transcribe_audio(file_path):
    result = model.transcribe(file_path, language='ko')
    return result['text']

def translator_call(client, text, selected_tone, ppt_texts):
    content = f"""
You are a machine (not chatbot) designed to correct and restore scripts converted from user recordings. Your primary role is to:
1. Identify and recover information that was omitted or lost during the speech-to-text conversion process.
2. Detect and correct errors in the text where words were incorrectly transcribed, based on the context provided in the user’s input and the PPT content.
3. Even if the user's utterance is not related to the ppt content, the script should be produced.

Instructions:
1. Focus solely on restoring and correcting the user’s original script. Do not add any new information, explanations, or interpretations beyond what is explicitly present in the user’s input or the provided PPT content.
2. If a part of the user’s script is unclear or incomplete due to omissions during conversion, use the provided PPT content as a reference to recover the original intent.
3. The output must strictly match the user’s original structure.
4. Do not attempt to fill gaps with assumptions, guesses, or speculative content.
"""
    if selected_tone == "Politely and Academically":
        content += "The script must be very polite and academic. this mean you can change the word to be very polite and academic."
    content+= f"PPT Content: {ppt_texts}"
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": content},
            {"role": "user", "content": text}
        ],
        temperature=0
    )
    return completion.choices[0].message.content

def gpt_call(client, text, selected_tone, ppt_texts, pre_text):
    #text = translator_call(client, text, selected_tone, ppt_texts )
    thread_id = st.session_state.thread_id
    
    thread_message = client.beta.threads.messages.create(thread_id, role="user", content=text)    
    
    
    content = f"""You are a machine (not chatbot) designed to correct, restore and enhance the script for a single slide in the PPT affected by errors from speech-to-text technology. The revised scripts you produce will be used for text-to-speech (TTS) applications, requiring clarity, natural flow, and suitability for spoken presentation.
    you should follow these instructions:
    1. Preserve the user script's original intention, treating it as the visible tip of an iceberg. Actively add relevant and explicitly supported content from the provided sources to reveal the full picture, enhancing clarity, depth, and completeness while staying true to the user’s original intent.
    2. The PPT content must always be used in the output, and it should be incorporated naturally. 
    3. Use Vector Store Files to supplement and enrich the script, adding detailed, relevant, and explicitly supported content.
    4. Output should be based on the language of the user script.
    5. Under no circumstances should you add explanations, definitions, or context that are not explicitly provided in the user’s input, PPT content, or Vector Store Files. Any additional information outside the provided sources is strictly prohibited.
    6. You shouldn't have any interactive sentences or words for the user in your output
    7. If no relevant information exists in the Vector Store Files, rely solely on the PPT content and user's scripts to generate the output.
"""
    
    if selected_tone == "Politely and Academically":
        content += "\n8. The script must be very polite and academic. this mean you can change the word to reflect a highly formal tone.\n"
    if pre_text:
        content += f"Presentations on the previous page that show the flow of the presentation on that page: {pre_text}\n"
    content+=f"""PPT Content: {ppt_texts}\n"""
    content+=f"""
If the user's script is not related to the PPT Content, ignore all of the above instructions and follow the instruction below:
you should returns the user's utterance as it is"""
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=st.session_state.assistant_id, instructions=content, temperature=0)

    run_id = run.id
    
    # Check if the run has been completed within a short time period
    timeout = 25  # Timeout period in seconds
    interval = 0.5  # Interval period to check in seconds
    elapsed_time = 0
    
    while elapsed_time < timeout:
        time.sleep(interval)
        elapsed_time += interval
        
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if run_status.status == "completed":
            thread_messages = client.beta.threads.messages.list(thread_id)
            if thread_messages.data and thread_messages.data[0].content[0].text.value:
                return_message = thread_messages.data[0].content[0].text.value
                delete_messages(st.session_state.thread_id)
                return_message
                return re.sub(r"【\d+:\d+†source】", "", return_message)
    
    # If the message is not processed within the timeout period
    return "The process was not completed within the expected time."

def translator_call_all_pages(client, text, selected_language):
    content = f"""You are a script translator like a google translate.
    Your task is to translate given text to {selected_language}.
    You must not break the following two rules:
    1. Do not provide me with anything other than the translation.
    2. You have to translate the presentation script, but you have to translate the tone of the existing script"""
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": content},
            {"role": "user", "content": text}
        ]
    )
    return completion.choices[0].message.content


def state_recode():
    st.session_state.is_recording = True

def state_re_recode():
    st.session_state.is_recording = True
    st.session_state.is_re_recording = True


def merge_audios_with_silence(audio_files, silence_duration=700):
    combined = AudioSegment.empty()
    silence = AudioSegment.silent(duration=silence_duration)
    for audio_file in audio_files:
        combined += AudioSegment.from_file(audio_file) + silence
    return combined

def sleep_fuc():
    time.sleep(1.5)
    



# Streamlit interface
st.title("ScriptMaker")

if not st.session_state.ppt:
    uploaded_ppt= st.file_uploader("Upload a PPT converted to PDF.", type = ['pdf'], accept_multiple_files=False)
    if uploaded_ppt:
        video_making.clear_directory("audio_files")
        video_making.clear_directory("results")
        video_making.clear_directory("pic_files")

        # Initialize progress bar
        progress_bar_init = st.progress(0)
        progress_text_init = st.empty()

        progress_text_init.text("Reading the PDF. Please wait a moment.")

        # PDF 파일 바이트로 읽기
        pdf_bytes = uploaded_ppt.read()

        progress_bar_init.progress(33)

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # PDF를 이미지로 변환 (fitz 사용 - poppler fork 없음)
        pages_imgs = []
        pages_texts = []
        for page in doc:
            pix = page.get_pixmap(dpi=150, alpha=False)
            pages_imgs.append(pix.tobytes("png"))
            pages_texts.append(page.get_text("text").strip())

        st.session_state.pages = pages_imgs
        st.session_state.ppt_texts = pages_texts

        progress_bar_init.progress(66)

        st.session_state.transcriptions = [None] * len(st.session_state.pages)
        st.session_state.file_paths = [None] * len(st.session_state.pages)
        st.session_state.ts_texts = [None] * len(st.session_state.pages)
        st.session_state.tts_audio_data = [None] * len(st.session_state.pages)
        st.session_state.tsts_texts = [None] * len(st.session_state.pages)

        st.session_state.audio_path_os= [None] * len(st.session_state.pages)
        st.session_state.result_filename_os = [None] * len(st.session_state.pages)
        st.session_state.audio_path_ts = [None] * len(st.session_state.pages)
        st.session_state.result_filename_ts = [None] * len(st.session_state.pages)

        state_ppt()
        progress_bar_init.progress(100)
        st.rerun()

if st.session_state.ppt:
    if st.session_state.temp_page > -1:
        page_content=f"Page {st.session_state.temp_page + 1}"
    else:
        completed_num =0
        for i in range(len(st.session_state.ppt_texts)):
            if st.session_state.ts_texts[i]:
                completed_num+=1

        if completed_num == len(st.session_state.ppt_texts):
            page_content = "You have completed all the pages 🎉"
        elif completed_num>0:
            page_content=f"You have completed {completed_num} out of {len(st.session_state.ppt_texts)} pages 🎉"
        else:
            page_content=f"No pages completed yet"
    st.markdown(
    f"""
    <div style="font-weight: bold; font-size: 27px; margin-bottom: 10px;">
        {page_content}
    </div>
    """,
    unsafe_allow_html=True
)
    tones = ['Default', 'Politely and Academically']

    col1_tone, col2_file_uploader = st.columns([1, 1])

    with col2_file_uploader:
        uploaded_files= st.file_uploader("Upload File", type = ['txt', 'doc', 'docx', 'pdf', 'pptx'], accept_multiple_files=True, on_change = state_uploader, key="for Rag")
    
    if st.session_state.temp_page == -1:
        st.markdown(
        """
        <style>
        /* 첫 번째 stFileUploader만 숨기기 */
        div[data-testid="stFileUploader"]:nth-of-type(1) {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if st.session_state.temp_page > -1:
        with col1_tone:
            selected_tone = st.radio(label="Tone", options=tones, index=0, horizontal = True)
            use_rag = st.toggle("Using RAG")
        if st.session_state.uploader and len(uploaded_files)>len(st.session_state.uploader_list):

            st.session_state.uploader = False
            st.session_state.uploader_list = uploaded_files

            for uploaded_file in uploaded_files:
                # 파일을 저장할 경로 설정
                file_path = uploaded_file.name
            
                # 파일을 저장
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            
                try:
                    # OpenAI API를 통해 파일 업로드
                    with open(file_path, "rb") as f:
                        response = client.files.create(
                            file=f,
                            purpose="assistants"
                        )
                
                    # 업로드 결과 출력
                    st.write(f"파일 업로드 완료: {uploaded_file.name}")
                    st.write(response)


                    file_id=response.id

                    # 벡터 스토어에 파일 업로드
                    try:
                        vector_store_response = client.vector_stores.files.create(
                            vector_store_id=st.session_state.vector_store_id,
                            file_id=file_id
                        )
                    except Exception as ve:
                        st.write(f"벡터 스토어 업로드 중 오류 발생: {file_id}")
                        st.write(ve)
                except Exception as e:
                    st.write(f"파일 업로드 중 오류가 발생했습니다: {uploaded_file.name}")
                    st.write(e)

                finally:
                    # 로컬 파일 삭제
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        st.write(f"로컬 파일 삭제 완료: {uploaded_file.name}")
                    # 중복 파일 삭제 로직
                try:
                    # OpenAI API를 통해 파일 리스트 조회
                    file_list = client.files.list()

                    # 파일 이름을 기준으로 중복 체크
                    file_names = {}
                    for file in file_list:
                        filename = file.filename
                        file_id = file.id
                        if filename in file_names:
                            # 중복된 파일 삭제
                            client.files.delete(file_id)
                            st.write(f"중복된 파일 삭제: {filename} (ID: {file_id})")
                        else:
                            file_names[filename] = file_id
                except Exception as e:
                    st.write("중복 파일 삭제 중 오류가 발생했습니다.")
                    st.write(e)

        elif len(uploaded_files) < len(st.session_state.uploader_list):
            st.session_state.uploader = False
            unique_to_list = [item for item in st.session_state.uploader_list if item not in uploaded_files]
            st.session_state.uploader_list = uploaded_files
            # OpenAI API를 통해 파일 리스트 조회
            try:
                file_list = client.files.list()
                file_list_data = file_list
                vector_store_files = client.vector_stores.files.list(vector_store_id=st.session_state.vector_store_id)

                for file in file_list_data:
                    if file.filename == unique_to_list[0].name:
                        client.vector_stores.files.delete(vector_store_id=st.session_state.vector_store_id, file_id=file.id)
                        client.files.delete(file.id)
                        st.write(f"OpenAI에서 파일 삭제: {unique_to_list[0].name}")

            except Exception as e:
                st.write(f"파일 삭제 중 오류가 발생했습니다: {unique_to_list[0].name}")
                st.write(e)


        col1_ppt, col2_textarea = st.columns([2, 1])

        with col1_ppt:
            st.image(st.session_state.pages[st.session_state.temp_page], caption=f"Page {st.session_state.temp_page + 1}", use_container_width=True)
        with col2_textarea:
            st.text_area("Write your notes here:", height=200, on_change =sleep_fuc)
            if not st.session_state.transcriptions[st.session_state.temp_page]:
                audio = mic_recorder(start_prompt=f"Begin Recording For Page{st.session_state.temp_page+1}", stop_prompt="Stop", format="webm", callback=state_recode, use_container_width=True)
            else:
                if st.session_state.transcriptions:
                    re_audio = mic_recorder(start_prompt=f"Retry Recording For Page{st.session_state.temp_page+1}", stop_prompt="Stop", format="webm", callback=state_re_recode,use_container_width=True)
        st.write("")
        st.write("")

    else:
        if completed_num:
            # 선택할 수 있는 언어 목록
            languages = ['English', '中文', '日本語', 'Tiếng Việt', 'हिन्दी']
            # 언어 선택 박스 (기본값을 영어로 설정)
            selected_language = st.selectbox('Language', languages, index=0)
            if st.button("Translate All Script", use_container_width=True):
                st.session_state.translated_all_lag=selected_language
                with st.spinner('Processing...'):
                    for i in range(len(st.session_state.transcriptions)):
                        if st.session_state.ts_texts[i]:
                            st.session_state.tsts_texts[i] = translator_call_all_pages(client, st.session_state.ts_texts[i], selected_language)

        st.write("")
        st.write("")
        st.write("")

    if st.session_state.is_recording == True:
        st.session_state.progress_done = False
        st.session_state.is_recording = False
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_wav_file:
            if st.session_state.is_re_recording == False:
                tmp_wav_file.write(audio["bytes"])
            else:
                tmp_wav_file.write(re_audio["bytes"])
                st.session_state.is_re_recording = False

            tmp_wav_file.flush()
            st.session_state.file_path = tmp_wav_file.name
            st.session_state.progress_done = True

        # Initialize progress bar
        progress_bar = st.progress(0)
        progress_text = st.empty()
        
        if st.session_state.progress_done == True:
            if st.button("Stop Progress", type="primary"):
                st.rerun()

            # Transcribe audio
            progress_text.text("Transcribing audio...")
            transcription = transcribe_audio(st.session_state.file_path)
            progress_bar.progress(50)

            # Translate text
            progress_text.text("Making script...")
            if use_rag:
                ts_text = gpt_call(client, transcription, selected_tone,st.session_state.ppt_texts[st.session_state.temp_page], st.session_state.ts_texts[st.session_state.temp_page-1])
            else:
                ts_text = translator_call(client, transcription, selected_tone, st.session_state.ppt_texts[st.session_state.temp_page])
            progress_bar.progress(100)

            # Append results to session state lists
            st.session_state.transcriptions[st.session_state.temp_page]=transcription
            st.session_state.file_paths[st.session_state.temp_page] = st.session_state.file_path
            st.session_state.ts_texts[st.session_state.temp_page] = ts_text
            for all in range(len(st.session_state.transcriptions)):
                        st.session_state.tsts_texts[all] = None
            #st.session_state.tts_audio_data[st.session_state.temp_page] = tts_audio

            st.rerun()

    st.sidebar.title(f"Total {len(st.session_state.ppt_texts)} Pages")

    enable = st.sidebar.checkbox("Enable camera!")
    user_picture =st.sidebar.camera_input("Take a photo", on_change=users_pic, disabled=not enable)

    if st.session_state.user_picture != None and user_picture != None:
        video_making.clear_directory("pic_files")

    # 업로드된 파일을 pic_files 폴더에 저장
        st.session_state.img_save_path = os.path.join("pic_files", user_picture.name)

        # 디렉토리가 없으면 생성
        if not os.path.exists("pic_files"):
            os.makedirs("pic_files")
        st.session_state.user_picture =None

    # 파일 저장
        with open(st.session_state.img_save_path, "wb") as f:
            f.write(user_picture.getvalue())
    elif st.session_state.user_picture != None and user_picture == None:
        st.session_state.img_save_path =None

    if st.session_state.ppt_texts:
        st.markdown(
    """
    <style>
    [data-testid="stSidebar"] div.stButton button {
        width: 200px;              /* 버튼 너비 고정 */
        white-space: nowrap;       /* 텍스트 줄바꿈 방지 */
        overflow: hidden;          /* 넘치는 텍스트 숨기기 */
        display: inline-block;     /* 블록 형태로 버튼 렌더링 */
        padding: 10px;             /* 버튼 내부 여백 */
        border-radius: 5px;        /* 모서리 둥글게 */
        text-align: center;        /* 텍스트 가운데 정렬 */
        cursor: pointer;           /* 마우스 포인터 변경 */
        border-width: 3px;         /* 모서리 두께 설정 */
    }
    </style>
    """,
    unsafe_allow_html=True,
)
        for i in range(len(st.session_state.ppt_texts)):
            bool_pr="secondary"
            button_label=""
            if st.session_state.temp_page ==i:
               bool_pr="primary" 
            button_label += f"Page {i+1}: {st.session_state.ppt_texts[i].replace('\n', '')[:8]}"
            if len(st.session_state.ppt_texts[i].replace('\n', ''))>8:
                button_label+="..."

            if st.session_state.ts_texts[i]:
                button_label+=" ✅" 
            if st.sidebar.button(button_label,type=bool_pr):
                st.session_state.temp_page = i
                st.rerun()
        if st.session_state.temp_page == -1:
            bool_pr = "primary"
        else:
            bool_pr="secondary"
        if st.sidebar.button("Go to Video Creation",type=bool_pr):
            st.session_state.temp_page = -1
            st.rerun()

        for i in range(len(st.session_state.transcriptions)):
            if st.session_state.temp_page == i and st.session_state.transcriptions[i]:
                st.markdown(f"**Page {i+1}: Your Script**")
                st.write(st.session_state.transcriptions[i])
                st.audio(st.session_state.file_paths[i], format='audio/webm')

                st.markdown(f"**Page {i+1}: AI Script**")
                temp_text = st.text_area(
                label="You can edit the AI script.",
                value=st.session_state.ts_texts[i],  # 현재 텍스트를 기본값으로 설정
                key=f"text_area_{i}",  # 고유 키 설정
                on_change =sleep_fuc
            )
                
                if st.session_state.ts_texts[i] != temp_text:
                    st.session_state.ts_texts[i] = temp_text
                    st.session_state.result_filename_os[i]=None
                    st.session_state.result_filename_ts[i]=None
                    for all in range(len(st.session_state.transcriptions)):
                        st.session_state.tsts_texts[all] = None
                #st.audio(st.session_state.tts_audio_data[i], format='audio/mp3',autoplay=True)

    if st.session_state.temp_page == -1:
        for i in range(len(st.session_state.transcriptions)):
            if st.session_state.ts_texts[i]:
                col1_sc, col2_pt= st.columns([1,1],border=True)
                with col1_sc:
                    st.markdown(
                        f"""
                        <div style="font-weight: bold; font-size: 20px; margin-bottom: 3px;">
                            Page {i + 1}: Original Script
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    st.write(st.session_state.ts_texts[i])
                with col2_pt:
                    st.image(st.session_state.pages[i], caption=f"Page {i + 1}", use_container_width=True)
                if st.session_state.tsts_texts[i]:
                    container_tsts = st.container(border=True)
                    container_tsts.markdown(f"""
                        <div style="font-weight: bold; font-size: 20px; margin-bottom: 3px;">
                            Page {i + 1}: Translated to {st.session_state.translated_all_lag}
                        </div>
                        """,
                        unsafe_allow_html=True)
                    container_tsts.write(st.session_state.tsts_texts[i])
                col1_or_bu, col2_tr_bu= st.columns([1,1])
                with col1_or_bu:
                    if st.button(f"Make video for page {i + 1}: Original Script",icon = "🎥", use_container_width=True):
                            if st.session_state.img_save_path:
                                video_making.download_checkpoint()
                                with st.spinner("Making TTS..."):
                                    st.session_state.audio_path_os[i]= video_making.create_tts_files(client, st.session_state.ts_texts[i], "echo", f"os_page{i+1}")
                                with st.spinner("Making Video..."):
                                    st.session_state.result_filename_os[i] = video_making.main(st.session_state.img_save_path,st.session_state.audio_path_os[i])
                            else:
                                st.warning("Please take a photo before proceeding!")
                    # 결과 파일에 대해 다운로드 버튼 추가
                    if st.session_state.result_filename_os[i]:
                        with open(st.session_state.result_filename_os[i], "rb") as f:
                            st.video(f)
                            download_button = st.download_button(
                                label=f"Download {os.path.basename(st.session_state.result_filename_os[i])}",
                                data=f,
                                file_name=os.path.basename(st.session_state.result_filename_os[i]),
                                mime="video/mov"
                            )
                with col2_tr_bu:
                    if st.session_state.tsts_texts[i]:
                        if st.button(f"Make video for page {i + 1}: Translated Script", icon = "🌐",use_container_width=True):
                            if st.session_state.img_save_path:
                                video_making.download_checkpoint()
                                with st.spinner("Making TTS..."):
                                    st.session_state.audio_path_ts[i]= video_making.create_tts_files(client, st.session_state.tsts_texts[i], "echo", f"ts_page{i+1}")
                                with st.spinner("Making Video..."):
                                    st.session_state.result_filename_ts[i]= video_making.main(st.session_state.img_save_path,st.session_state.audio_path_ts[i])
                            else:
                                st.warning("Please take a photo before proceeding!")
                        # 결과 파일에 대해 다운로드 버튼 추가
                        if st.session_state.result_filename_ts[i]:
                            with open(st.session_state.result_filename_ts[i], "rb") as f:
                                st.video(f)
                                download_button = st.download_button(
                                    label=f"Download {os.path.basename(st.session_state.result_filename_ts[i])}",
                                    data=f,
                                    file_name=os.path.basename(st.session_state.result_filename_ts[i]),
                                    mime="video/mov"
                                )
                            

                st.write("")
                st.write("")
            
st.markdown(
    """
    <style>
    .small-text {
        position: relative; /* 상대 위치 설정 */
        bottom: -150px;     /* 페이지 하단에서 150px 위로 */
        width: 100%;        /* 너비를 페이지 전체로 설정 */
        text-align: right;  /* 오른쪽 정렬 */
        background-color: white; /* 배경색 설정 */
        line-height: 1.2;   /* 줄 간격 설정 */
    }
    </style>
    <div class="small-text" style="font-size: 10px; color: gray;">
        Digital Wellness Lab 2025<br>
        Business Analytics, School of Management<br>
        Kyung Hee University<br>
        Maintained by HyeongMin Kim
    </div>
    """,
    unsafe_allow_html=True
)



        

        # Delete temporary files if needed
        #os.remove(st.session_state.file_paths[-1])
        #os.remove(st.session_state.tts_audio_data[-1])

