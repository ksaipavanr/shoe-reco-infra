# # # Placeholder lambda handler - replace with your actual code
# # def lambda_handler(event, context):
# #     return {'statusCode':200,'body':'hello from bedrock_agent'}
# import json
# import boto3
# import logging

# # Setup logging
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)

# def lambda_handler(event, context):
#     try:
#         # Log the event for debugging purposes
#         logger.info(f"Event: {json.dumps(event)}")

#         # Ensure that 'httpMethod' is in the event
#         if 'httpMethod' in event:
#             if event['httpMethod'] == 'OPTIONS':
#                 return {
#                     'statusCode': 200,
#                     'headers': {
#                         'Access-Control-Allow-Origin': '*',
#                         'Access-Control-Allow-Headers': '*',
#                         'Access-Control-Allow-Methods': 'OPTIONS,POST'
#                     },
#                     'body': ''
#                 }

#         body = json.loads(event.get('body', '{}'))
#         user_input = body.get('user_input', '')
#         session_id = body.get('session_id', '')

#         logger.info(f"Received input: {user_input}, session: {session_id}")

#         # Initialize the Bedrock runtime client
#         bedrock_runtime = boto3.client('bedrock-agent-runtime')

#         # Invoke the Bedrock agent
#         response = bedrock_runtime.invoke_agent(
#             agentId='NUMUKEJDAB',  # Use the correct agentId
#             # agentAliasId='YZLLYUO2DA',  # Use the correct aliasId
#             #agentAliasId='VUCCKUE92I',  # Use the correct aliasId
#             # agentAliasId='H6RTZYXSEX',  # Use the correct aliasId
#             # agentAliasId='UHQAEWBPRT',  # Use the correct aliasId
#             # agentAliasId='DHHX72LSP3',  # Use the correct aliasId
#             agentAliasId='UEOYXK8FMH',  # Use the correct aliasId
#             sessionId=session_id,
#             inputText=user_input
#         )

#         result = response['completion']
#         full_response = ""

#         # Process the completion response
#         for events in result:
#             if 'chunk' in events:
#                 payload = events['chunk']['bytes'].decode('utf-8')
#                 full_response = payload

#         logger.info(f"Full response: {full_response}")

#         return {
#             'statusCode': 200,
#             'headers': {
#                 'Access-Control-Allow-Origin': '*',
#                 'Access-Control-Allow-Headers': '*',
#                 'Access-Control-Allow-Methods': 'OPTIONS,POST'
#             },
#             'body': json.dumps({'response': full_response})

#         }
#     except Exception as e:
#         logger.error(f"Error occurred: {str(e)}")
#         return {
#             'statusCode': 500,
#             'headers': {
#                 'Access-Control-Allow-Origin': '*',
#                 'Access-Control-Allow-Headers': '*',
#                 'Access-Control-Allow-Methods': 'OPTIONS,POST'
#             },
#             'body': json.dumps({'error': 'Internal Server Error'})
#         }
import json
import boto3
import logging
import uuid

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock_runtime = boto3.client("bedrock-agent-runtime")

def lambda_handler(event, context):
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Handle CORS Preflight
        if event.get("httpMethod") == "OPTIONS":
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST'
                },
                'body': ''
            }

        body = json.loads(event.get("body", "{}"))

        # Your client sends:  user_name + query
        user_name = body.get("user_name", "user")
        user_input = body.get("query", "")
        session_id = body.get("session_id", "")

        # Fix: ALWAYS generate a valid session ID
        if not session_id or len(str(session_id)) < 2:
            session_id = f"{user_name}-{uuid.uuid4().hex[:8]}"

        logger.info(f"Final SessionID Used: {session_id}")
        logger.info(f"User Input: {user_input}")

        # TODO → replace with your NEW agentId
        AGENT_ID = "NUMUKEJDAB"

        # TODO → replace with your NEW aliasId
        AGENT_ALIAS_ID = "UEOYXK8FMH"

        # Invoke the Bedrock Agent
        response = bedrock_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=user_input
        )

        # Process streaming response
        result = response.get("completion", [])
        full_response = ""

        for event_part in result:
            chunk = event_part.get("chunk")
            if chunk:
                text = chunk["bytes"].decode("utf-8")
                full_response += text

        logger.info(f"Agent Response: {full_response}")

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({
                "response": full_response,
                "session_id": session_id
            })
        }

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({'error': 'Internal Server Error'})
        }
