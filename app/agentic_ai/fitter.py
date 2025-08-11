from autogen_agentchat.agents import AssistantAgent

prompt=f"(You just have to Adjust the code in the given block of code.Logic and approach must remian same.System and code must be consistent (ACID))+{structure}"
class FitterAgent():
    def __init__(self,llm,prompt):
        self.fitter=AssistantAgent(
            name="Fitter",
            description="role is to adjust the code according to the user need",
            model_client=llm,
            system_message=prompt
        )