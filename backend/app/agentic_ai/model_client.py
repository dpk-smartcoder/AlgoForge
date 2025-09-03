from autogen_ext.models.openai import OpenAIChatCompletionClient

class Model_Client():
    def __init__(self,model:str,API_KEY:str):
        self.client=OpenAIChatCompletionClient(
            model=model,
            api_key=API_KEY
        )
    

    def getClient(self):
        return self.client