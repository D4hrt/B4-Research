from tinytroupe.agent import TinyPerson
from tinytroupe.agent.human_controlled_person import HumanControlledPerson
from tinytroupe.environment import TinyWorld
from tinytroupe.factory import TinyPersonFactory
from tinytroupe.extraction import ResultsExtractor

import json
import os

# APIキーの設定（環境変数 OPENAI_API_KEY を事前に設定してください）
assert os.environ.get("OPENAI_API_KEY"), "環境変数 OPENAI_API_KEY が設定されていません"

factory = TinyPersonFactory("Workshop for Creating New Japanese Industries")
company_manager = factory.generate_person(
  """
  Marketing Manager at a travel services company. A pragmatist who prioritizes market trends and data.
  Sensitive to target demographics and revenue models, placing feasibility above all else.
  More interested in creating “systems that sell” than in novel ideas.
  """
)
freelance_planner = factory.generate_person(
  """
  Freelance travel concept creator. An idea-driven professional who values unique concepts and experiences.
  Emphasizes design, emotional value, and storytelling.
  Prioritizes the thrill of travel over practical constraints.
  """
)
haruto = HumanControlledPerson.load_specification("./tinytroupe/examples/human/my_persona.json")

company_manager.save_specification("./try/brainstorm_travel/company_manager.json")
freelance_planner.save_specification("./try/brainstorm_travel/freelance_planner.json")

world = TinyWorld("Meeting Room", [company_manager, freelance_planner, haruto])
world.make_everyone_accessible()

instruct = '''
Discuss the new travel service “Destination Wardrobe Rental Service.”
Here is the description of the travel service.
・A system allowing you to rent clothing and accessories locally, tailored to your destination.
・Travel light—just pack your essentials and return the items when you leave.
・Aims to provide an eco-friendly and hassle-free travel experience.
'''


world.broadcast(instruct)

world.run(2)