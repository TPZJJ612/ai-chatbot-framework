import logging
import os

import html2text
import json_log_formatter
from app.core.intentClassifier import IntentClassifier
from app.stories.models import Story
from app.core import nlp
from app.core import sequenceLabeler
from bson import ObjectId
from flask import Blueprint, request, render_template,request, send_file

from app.commons import errorCodes
from app.commons import buildResponse

formatter = json_log_formatter.JSONFormatter()
json_handler = logging.FileHandler(filename='log.json')
json_handler.setFormatter(formatter)

logger = logging.getLogger('my_json')
logger.addHandler(json_handler)
logger.setLevel(logging.INFO)
# logging ends



endpoint = Blueprint('api', __name__, url_prefix='/api')

# Request Handler
@app.route('/api/v1', methods=['POST'])
def api():
    requestJson = request.get_json(silent=True)
    resultJson = requestJson

    if requestJson:
        intentClassifier = IntentClassifier()
        storyId = intentClassifier.predict(requestJson.get("input"))
        story = Story.objects.get(id=ObjectId(storyId))
        if story.parameters:
            parameters = story.parameters
        else:
            parameters=[]

        if ((requestJson.get("complete") is None) or (requestJson.get("complete") is True)):
            resultJson["intent"] = {
                "name":story.intentName,
                "storyId":str(story.id)
            }

            if parameters:
                extractedParameters= sequenceLabeler.predict(storyId,
                                                             requestJson.get("input")
                                                             )
                missingParameters = []
                resultJson["missingParameters"] =[]
                resultJson["extractedParameters"] = {}
                resultJson["parameters"]=[]
                for parameter in parameters:
                    resultJson["parameters"].append({
                        "name": parameter.name,
                        "required": parameter.required
                    })

                    if parameter.required:
                        if parameter.name not in  extractedParameters.keys():
                            resultJson["missingParameters"].append(parameter.name)
                            missingParameters.append(parameter)

                resultJson["extractedParameters"] = extractedParameters
                if missingParameters:
                    resultJson["complete"] = False
                    currentNode = missingParameters[0]
                    resultJson["currentNode"] = currentNode["name"]
                    resultJson["speechResponse"] = currentNode["prompt"]
                else:
                    resultJson["complete"] = True
                    resultJson["speechResponse"] = story.speechResponse
            else:
                resultJson["complete"] = True
                resultJson["speechResponse"] = story.speechResponse

        elif (requestJson.get("complete") is False):
            if "cancel" not in story.intentName:
                storyId = requestJson["intent"]["storyId"]
                story = Story.objects.get(id=ObjectId(storyId))
                resultJson["extractedParameters"][requestJson.get("currentNode")] = requestJson.get("input")

                resultJson["missingParameters"].remove(requestJson.get("currentNode"))

                if len(resultJson["missingParameters"])==0:
                    resultJson["complete"] = True
                    resultJson["speechResponse"] = story.speechResponse
                else:
                    missingParameter = resultJson["missingParameters"][0]
                    resultJson["complete"] = False
                    currentNode = [node for node in story.parameters if missingParameter in node.name][0]
                    resultJson["currentNode"] = currentNode.name
                    resultJson["speechResponse"] = currentNode.prompt
            else:
                resultJson["currentNode"] = None
                resultJson["missingParameters"] = []
                resultJson["parameters"] = {}
                resultJson["intent"] = {}
                resultJson["complete"] = True
                resultJson["speechResponse"] = story.speechResponse

    else:
        resultJson = errorCodes.emptyInput
    return buildResponse.buildJson(resultJson)




# Text To Speech
@app.route('/tts')
def tts():
    voices = {
              "american": "file://commons/fliteVoices/cmu_us_eey.flitevox"
              }
    os.system("echo \"" + request.args.get("text") + "\" | flite -voice " + voices["american"] + "  -o sound.wav")
    path_to_file = "../sound.wav"
    return send_file(
        path_to_file,
        mimetype="audio/wav",
        as_attachment=True,
        attachment_filename="sound.wav")