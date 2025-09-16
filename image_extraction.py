import os
import base64
from IPython.display import Image, display
import base64
from IPython.display import Image, display
from unstructured.partition.pdf import partition_pdf
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chat_models import init_chat_model

os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGCHAIN_ENDPOINT'] = 'https://api.smith.langchain.com'
os.environ['LANGCHAIN_API_KEY'] = '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'
os.environ["MISTRAL_API_KEY"] = "hrDF1J8v9kDfT9UZXss6oCXoJk46AZNO"
llm = init_chat_model("mistral-large-latest", model_provider="mistralai", temperature=0.0)
output_path = "./content"
file_path = "./docs/ERCS_4G_PM_SOP.pdf"

chunks = partition_pdf(
    filename=file_path,
    infer_table_structure=True,
    strategy="hi_res",
    extract_image_block_types=["Image"],
    extract_images_in_pdf=True,
    extract_image_block_to_payload=True,
    max_characters=10000,
    combine_text_under_n_chars=2000,
    new_after_n_chars=6000,
)

# Get the images from the CompositeElement objects
def get_images_base64(chunks):
    images_b64 = []
    for chunk in chunks:
        if "Image" in str(type(chunk)):
            print("Found Image")
            images_b64.append(chunk.metadata.image_base64)
            # chunk_els = chunk.metadata.orig_elements
            # for el in chunk_els:
            #     if "Image" in str(type(el)):
            #         images_b64.append(el.metadata.image_base64)
    return images_b64

images = get_images_base64(chunks)


def display_base64_image(base64_code):
    # Decode the base64 string to binary
    image_data = base64.b64decode(base64_code)
    # Display the image
    display(Image(data=image_data))

display_base64_image(images[0])


prompt_template = """Describe the image in detail. For context,
                  the image is part of a research paper explaining the transformers
                  architecture. Be specific about graphs, such as bar plots."""
messages = [
    (
        "user",
        [
            {"type": "text", "text": prompt_template},
            {
                "type": "image_url",
                "image_url": {"url": "data:image/jpeg;base64,{image}"},
            },
        ],
    )
]


prompt = ChatPromptTemplate.from_messages(messages)

chain = prompt | llm | StrOutputParser()


image_summaries = chain.batch(images)

print(image_summaries)