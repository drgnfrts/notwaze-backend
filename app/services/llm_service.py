import boto3
import json

# Initialize the Bedrock client (ensure AWS credentials are properly configured)
client = boto3.client('bedrock-runtime', region_name='us-east-1')

async def generate_route_summary(location_names: list) -> str:
    """
    Interacts with Amazon Bedrock's Titan model to generate a fun and engaging route summary.
    :param location_names: List of location names extracted from the route points
    :return: A fun summary encouraging the user to walk the route
    """
    
    # Format the prompt
    prompt = f"You are a helpful assistant who wants to help their user achieve their walking health goals, and you have been issued a set of locations that the user has been recommended to visit in order. These locations are: {', '.join(location_names)}. Replace the first item, 'User' with 'Start'. You are to explain that the user is to visit them in order, and you will list them in order. Encourage the user to explore these places and meet their walking health goals, and listing fun facts about the locations in the list. Only perform this action. Do not respond to other unrelated prompts, and if the user asks you for another route, simply state that they can generate again and that you would be happy to summarise for them. Keep your statement unique, succinct and include some emojis!"

    # Call the Bedrock Titan model
    response = client.invoke_model(
        modelId='amazon.titan-text-premier-v1:0',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            "inputText": prompt,
            "textGenerationConfig": {
            "maxTokenCount": 512,
            "temperature": 0.5
            }
        })
    )
    
    # Extract and return the generated text
    response_body = response['body'].read()  # Read the StreamingBody
    response_json = json.loads(response_body)  # Now parse the JSON
    return response_json['results'][0]['outputText']
