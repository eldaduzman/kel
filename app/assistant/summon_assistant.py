import os
import time

from app.inputs.inputs import get_assistant_inputs

from openai import OpenAI
from rich.progress import Progress

from app.config import get_configs as config
from app.utils.utils import print_in_color


class Assistant:

    def __init__(self, assistant_name, file):
        self.assistant_name = assistant_name
        self.file = file
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.file = self.client.files.create(
            file=open(self.file, "rb"),
            purpose='assistants'
        )
        self.assistant = self.client.beta.assistants.create(
            name=self.assistant_name,
            instructions=config.get_openai_assistant_instructions(),
            tools=[{"type": "code_interpreter"}, {"type": "retrieval"}],
            model=config.get_openai_assistant_model_name(),
            file_ids=[self.file.id],
        )

    def create_a_thread(self):
        return self.client.beta.threads.create()

    def add_message_to_thread(self, thread_id, content):
        return self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content,
        )

    def start_run(self, thread_id, assistant_id):
        return self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
        )

    def get_messages_and_print(self, thread_id, run_id):
        messages = self.client.beta.threads.messages.list(
            thread_id=thread_id,
        )

        for message in reversed(messages.data[:-1]):
            if message.role != "user" and message.run_id == run_id:
                print_in_color("Assistant: " + message.content[-1].text.value, config.get_info_color())

    def delete_assistant(self):
        if config.get_openai_delete_assistant_at_exit():
            self.client.beta.assistants.delete(self.assistant.id)
            self.client.files.delete(self.file.id)

        message = "Assistant and files have been deleted successfully." if config.get_openai_delete_assistant_at_exit() else "Assistant and files have not been deleted."
        print_in_color(message, config.get_warning_color())


def summon_assistant():
    assistant_name, file = vars(get_assistant_inputs()).values()

    print_in_color(f"Summoning an assistant...", config.get_info_color())
    print_in_color(f"""
            Not sure what to `Kel`? Try one of these:
            1: {config.get_openai_assistant_choices()[0]},
            2: {config.get_openai_assistant_choices()[1]},
            3: {config.get_openai_assistant_choices()[2]},
            4: {config.get_openai_assistant_choices()[3]},
    """, config.get_info_color())

    assistant = Assistant(assistant_name, file)
    get_user_question = input("Ask `Kel`: ")

    thread = assistant.create_a_thread()
    # print(f"Thread id: {thread.id}")

    while get_user_question != ":q" or get_user_question != ":quit":
        if get_user_question == ":q" or get_user_question == ":quit":
            print_in_color("Exiting chat mode", config.get_info_color())
            break

        choices = {
            "1": config.get_openai_assistant_choices()[0],
            "2": config.get_openai_assistant_choices()[1],
            "3": config.get_openai_assistant_choices()[2],
            "4": config.get_openai_assistant_choices()[3],
        }

        if int(get_user_question.strip()) not in choices:
            print_in_color("Invalid choice. Please try again.", config.get_warning_color())
            get_user_question = input("Ask `Kel`: ")
            continue

        if int(get_user_question.strip()) in choices:
            assistant.add_message_to_thread(thread.id, choices[get_user_question.strip()])
            run = assistant.start_run(thread.id, assistant.assistant.id)

        else:
            message = assistant.add_message_to_thread(thread.id, get_user_question)
            # print(f"Message id: {message.id}")
            run = assistant.start_run(thread.id, assistant.assistant.id)
            # print(f"Run id: {run.id} | Run status: {run.status}")

        with Progress(transient=True) as progress:
            task = progress.add_task("[cyan]Crunching...", total=100)

            while not progress.finished:
                while run.status != "completed":
                    run = assistant.client.beta.threads.runs.retrieve(
                        thread_id=thread.id,
                        run_id=run.id
                    )
                    time.sleep(1)
                    if run.status == "completed":
                        progress.update(task, advance=100)
                        break
                    progress.update(task, advance=1)

        assistant.get_messages_and_print(thread.id, run.id)

        get_user_question = input("Ask `Kel`: ")

    assistant.delete_assistant()
