# load config
import os

model_name = os.getenv("MODEL_NAME", "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")
layer_to_edit = os.getenv("LAYER_TO_EDIT", "model.layers[15].mlp.gate_proj.weight")
init_epsilon = float(os.getenv("EPS", "1.0"))
learning_rate = float(os.getenv("LR", "1.0"))
max_new_tokens = int(os.getenv("MAX_NEW_TOKENS", "512"))

# if there are no MODEL_PATH in environment, we will set it to ./model_cache
MODEL_PATH = os.getenv("MODEL_PATH", "")
if MODEL_PATH == "":
    MODEL_PATH = os.path.join(os.getcwd(), "model_cache")
os.environ["HF_HOME"] = MODEL_PATH
EDITED_MODEL_PATH = os.path.join(MODEL_PATH, "edited_model/model.pth")
LOAD_EDITED_MODEL = os.getenv("LOAD_EDITED_MODEL", None)
os.makedirs(os.path.join(MODEL_PATH, "edited_model"), exist_ok=True)

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, AsyncIterator
import uvicorn
from contextlib import asynccontextmanager
import traceback
import grace
from grace.editors import GRACE_barebones as GRACE
from grace.utils import tokenize_qa
import torch
import copy
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, AutoModelForCausalLM

model = None
tokenizer = None
edited_model = None
device = "cuda" if torch.cuda.is_available() else "cpu"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    print(f"Hugging Face cache directory set to: {os.environ['HF_HOME']}")
    print(f"CUDA Available: {torch.cuda.is_available()}")

    try:
        # Load the T5 model and tokenizer
        global model, tokenizer, edited_model, device

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        # if we already have edited model and want to load from it
        if LOAD_EDITED_MODEL and os.path.exists(EDITED_MODEL_PATH):
            print(f"Load saved model from {EDITED_MODEL_PATH}")
            edited_model = torch.load(EDITED_MODEL_PATH)
            edited_model.model = edited_model.model.to(device)

        if not edited_model:
            print(f"Load model {model_name}")
            model = AutoModelForCausalLM.from_pretrained(model_name)
            model = model.to(device)
            edited_model = GRACE(
                model,
                layer_to_edit,
                init_epsilon,
                learning_rate,
                device,
                generation=True,
            )
    except Exception as e:
        traceback.print_exc()
        print(f"Error prepare resource: {e}")
    yield


app = FastAPI(
    title="Robofin Models",
    description="Robofin Models",
    version="1.0.0",
    lifespan=lifespan,
)


class GenerateRequest(BaseModel):
    text: str


class EditRequest(BaseModel):
    text: str
    edit: str


@app.get("/health")
def health():
    """health check

    Returns:
        Dict[str, int]: {"status": 200} if the server is in healthy state
    """
    return {"status": 200}


@app.post("/predict", response_model=Dict[str, str])
def generate_text(request: GenerateRequest) -> Dict[str, str]:
    """
    Endpoint to generate a response based on the input text.

    Args:
        request (GenerateRequest): The request body containing the 'text' field.

    Returns:
        Dict[str, str]: A JSON response with a 'message' field.
    """
    try:
        text = request.text
        # input_encoding = tokenizer(
        #     [text],
        #     # padding="longest",
        #     # max_length=20,
        #     # truncation=True,
        #     return_tensors="pt",
        # )
        # preds = edited_model.generate(
        #     input_encoding["input_ids"].to(device),
        #     max_new_tokens=max_new_tokens,
        #     # do_sample=True,
        #     temperature=0.1,
        #     top_p=0.95,
        #     repetition_penalty=1.2,
        #     pad_token_id=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id,
        #     eos_token_id=tokenizer.eos_token_id,
        # ).squeeze()
        # answer = tokenizer.decode(preds, skip_special_tokens=True)

        # apply chat template <｜begin▁of▁sentence｜><｜User｜>text<｜Assistant｜><think>
        # text = tokenizer.apply_chat_template(
        #     conversation=[{"role": "user", "content": text}], return_tensors="pt", add_generation_prompt=True, return_dict=False, tokenize=False
        # )
        # text += "</think>"
        text = (
            f"<｜begin▁of▁sentence｜><｜User｜>{text}<｜Assistant｜><think>\n</think>"
        )
        # add </think> to remove think feature

        print(text)
        # tokenize
        input_encoding = tokenizer(
            [text],
            # padding="longest",
            max_length=max_new_tokens,
            truncation=True,
            return_tensors="pt",
            # add_special_tokens=False,
        )
        # generate
        preds = edited_model.generate(
            input_encoding["input_ids"].to(device),
            max_new_tokens=max_new_tokens,
            # do_sample=True,
            # temperature=0.1,
            # top_p=0.95,
            # repetition_penalty=1.2,
            pad_token_id=(
                tokenizer.pad_token_id
                if tokenizer.pad_token_id is not None
                else tokenizer.eos_token_id
            ),
            eos_token_id=tokenizer.eos_token_id,
        ).squeeze()
        # decode
        answer = tokenizer.decode(
            preds[input_encoding["input_ids"].shape[1] :], skip_special_tokens=True
        ).strip()
        return {"message": answer}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def torch_save_model(model):
    torch.save(edited_model, EDITED_MODEL_PATH)
    print(f"Save model to {EDITED_MODEL_PATH}")


@app.post("/edit", response_model=Dict[str, str])
def edit_text(
    request: EditRequest, background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """
    Endpoint to edit the model

    Args:
        request (EditRequest): The request body containing 'text' and 'edit' fields.

    Returns:
        Dict[str, str]: A JSON response with a 'message' field.
    """
    try:
        text = request.text
        edit = request.edit

        # edit_input = {
        #     "text": [text],
        #     "labels": [edit],
        # }

        # # input_encoding = tokenizer(
        # #     [text],
        # #     # padding="longest",
        # #     # max_length=20,
        # #     # truncation=True,
        # #     return_tensors="pt",
        # # )
        # text = tokenizer.apply_chat_template(
        #     conversation=[{"role": "user", "content": text}], return_tensors="pt", add_generation_prompt=True, tokenize=False
        # )
        # input_encoding = tokenizer(
        #     [text], return_tensors="pt", padding="max_length", max_length=max_new_tokens, truncation=True,
        # )

        # # input_ids, attention_mask = input_encoding.input_ids, input_encoding.attention_mask
        # input_ids, attention_mask = input_encoding["input_ids"], input_encoding["attention_mask"]

        # # target_encoding = tokenizer(
        # #     [edit],
        # #     # padding="longest",
        # #     # max_length=20,
        # #     # truncation=True,
        # #     return_tensors="pt",
        # # )
        # target_encoding = tokenizer(
        #     [edit],
        #     padding="max_length",
        #     max_length=max_new_tokens,
        #     truncation=True,
        #     return_tensors="pt",
        # )

        # # target_encoding = tokenizer.apply_chat_template(
        # #     conversation=[{"role": "user", "content": edit}], return_tensors="pt", add_generation_prompt=True, return_dict=True,
        # # )

        # labels = target_encoding.input_ids
        # # labels = target_encoding["input_ids"]
        # labels[labels == tokenizer.pad_token_id] = -100

        # edit_tokens = {
        #     "input_ids": input_ids,
        #     "attention_mask": attention_mask,
        #     "labels": labels,
        # }

        # print(edit_tokens)

        # edit_tokens = {f"{k1}": v1.to(device) for k1, v1 in edit_tokens.items()}
        # edited_model.edit(edit_tokens)

        # preds = edited_model.generate(
        #     edit_tokens["input_ids"].to(device),
        #     max_new_tokens=max_new_tokens,
        #     # do_sample=True,
        #     temperature=0.1,
        #     top_p=0.95,
        #     repetition_penalty=1.2,
        #     pad_token_id=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id,
        #     eos_token_id=tokenizer.eos_token_id,
        # ).squeeze()
        # new_answer = tokenizer.decode(preds, skip_special_tokens=True)

        # code from tokenize_gpt
        prompt = [text]
        label = [edit]
        mask_token = -100
        # add chat template <｜begin▁of▁sentence｜><｜User｜>prompt<｜Assistant｜>label<｜end▁of▁sentence｜> for editing
        # full_prompt = [
        #     tokenizer.apply_chat_template(
        #         conversation=[{"role": "user", "content": p}, {"role": "assistant", "content": l}], return_tensors="pt", add_generation_prompt=False, tokenize=False
        #     ) for p, l in zip(prompt, label)
        # ]
        full_prompt = [
            f"<｜begin▁of▁sentence｜><｜User｜>{p}<｜Assistant｜><think>\n</think>{l}<｜end▁of▁sentence｜>"
            for p, l in zip(prompt, label)
        ]
        # create labels with padding
        prompt_ids = tokenizer(
            list(prompt), return_tensors="pt", padding=True, truncation=True
        )["input_ids"]
        num_prompt_toks = [int((i != tokenizer.pad_token_id).sum()) for i in prompt_ids]
        tokens = tokenizer(
            full_prompt, return_tensors="pt", padding=True, truncation=True
        )
        tokens["labels"] = tokens["input_ids"].clone()
        for i in range(len(prompt)):
            tokens["labels"][i][: num_prompt_toks[i]] = mask_token

        tokens["labels"][tokens["input_ids"] == tokenizer.pad_token_id] = mask_token
        tokens = {f"{k1}": v1.to(device) for k1, v1 in tokens.items()}

        # code from grace/main.py
        edited_model.edit(tokens)

        # apply chat template <｜begin▁of▁sentence｜><｜User｜>text<｜Assistant｜><think>
        # text = tokenizer.apply_chat_template(
        #     conversation=[{"role": "user", "content": text}], return_tensors="pt", add_generation_prompt=True, return_dict=False, tokenize=False
        # )
        # text += "</think>"
        text = (
            f"<｜begin▁of▁sentence｜><｜User｜>{text}<｜Assistant｜><think>\n</think>"
        )
        print(text)
        # tokenize
        input_dicts = tokenizer(
            [text],
            # padding="longest",
            max_length=max_new_tokens,
            truncation=True,
            return_tensors="pt",
            # add_special_tokens=False,
        )
        # generate
        preds = edited_model.generate(
            input_dicts["input_ids"].to(device),
            max_new_tokens=max_new_tokens,
            # do_sample=True,
            # temperature=0.1,
            # top_p=0.95,
            # repetition_penalty=1.2,
            pad_token_id=(
                tokenizer.pad_token_id
                if tokenizer.pad_token_id is not None
                else tokenizer.eos_token_id
            ),
            eos_token_id=tokenizer.eos_token_id,
        ).squeeze()
        # decode
        new_answer = tokenizer.decode(
            preds[input_dicts["input_ids"].shape[-1] :], skip_special_tokens=True
        ).strip()
        print(f"After Editing. Question: {text}. Answer: {new_answer}")

        # save model in background
        background_tasks.add_task(torch_save_model, model=edited_model)
        return {"message": new_answer}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
