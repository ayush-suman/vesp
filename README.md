<div align="center">
    <h1>Vesp</h1>
</div>

<div align="center">
    </h3>Declarative Agentic Framework</h3>
</div>

<br>

Vesp is an open-source suite of packages designed to declaratively define, build and test AI agentic systems. 

### Separation of Concern
The framework allows you to write your prompt structure in json or yaml, separating the job of prompt engineering and writing the app business logic. This allows you to efficiently and quickly modify prompts without affecting other areas of code. 

### Layer of Abstraction
Vesp abstracts away the complex, and sometimes minute, differences between different vendor (OpenAI, Anthropic, Google etc.) APIs by letting you define your prompt structure in a way that works with all the vendors. This also allows you to quickly prototype and switch between different vendors without changing your agent code.

<br>

## Quickstart

```bash
uv add vesp[yaml, openai]
```

```yaml
# agents/digits_breakdown.yaml
- system: Convert the user input (integer) to words

- user: {input}
  params: [input]

- assistant: ~

- system: Breakdown the digits into the given schema

- assistant: ~
  tag: digits
  schema:
    name: digits_schema
    description: Extract the number into digits
    json_schema:
        type: object
        properties:
            millions:
                type: integer
            hundred_thousands:
                type: integer
            ten_thousands:
                type: integer
            thousands:
                type: integer
            hundreds:
                type: integer
            tens: 
                type: integer
            ones:
                type: integer
```


```python
# agents/__init__.py

from vesp import agent, Agent

@agent(name="Digits Breakdown Agent", prompt_structure="digits_breakdown.yaml")
class DigitBreakdownAgent(Agent):
    def handle_response(digits):
        '''Returns the sum of last 3 digits (hundreds, tens and ones)'''
        return digits.hundreds + digits.tens + digits.ones
```

```python
# main.py

from agents import DigitBreakdownAgent
from vesp import OpenAIChatCompletionGenerator

# Initialise and load agent with openai chat completion generator
openai_chat_completion = OpenAIChatCompletionGenerator(api_key=os.getenv("OPENAI_API_KEY"))
agent = DigitBreakdownAgent(generator=openai_chat_completion)

# Pass params to the agent
results = await agent(input=243942)





