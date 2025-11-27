# import logging
import re
from typing import Dict, Any
from http import HTTPStatus
import pymysql

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Email validation
def validate_email(email: str) -> bool:
    regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    return re.match(regex, email) is not None

# Phone number validation
def validate_phone(phone: str) -> bool:
    regex = r"^\+?[1-9]\d{1,14}$"
    return re.match(regex, phone) is not None

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        action_group = event['actionGroup']
        function = event['function']
        message_version = event.get('messageVersion', 1)
        parameters = event.get('parameters', [])

        param_map = {param['name'].lower(): param['value'] for param in parameters}
        name = param_map.get('name')
        email = param_map.get('email')
        phone_number = param_map.get('phone_number')

        logger.info('Received new user details: %s', param_map)

        # Validate inputs
        if not name or not email or not phone_number:
            missing = []
            if not name:
                missing.append("name")
            if not email:
                missing.append("email")
            if not phone_number:
                missing.append("phone number")
            return {
                'response': {
                    'actionGroup': action_group,
                    'function': function,
                    'functionResponse': {
                        'responseBody': {
                            'TEXT': {
                                'body': f"Please provide your {', '.join(missing)} to proceed with registration."
                            }
                        }
                    }
                },
                'messageVersion': message_version
            }

        if not validate_email(email):
            return {
                'response': {
                    'actionGroup': action_group,
                    'function': function,
                    'functionResponse': {
                        'responseBody': {
                            'TEXT': {
                                'body': "The email address provided is invalid. Please provide a valid email."
                            }
                        }
                    }
                },
                'messageVersion': message_version
            }

        if not validate_phone(phone_number):
            return {
                'response': {
                    'actionGroup': action_group,
                    'function': function,
                    'functionResponse': {
                        'responseBody': {
                            'TEXT': {
                                'body': "The phone number provided is invalid. Please provide a valid phone number."
                            }
                        }
                    }
                },
                'messageVersion': message_version
            }

        # Connect to RDS
        connection = pymysql.connect(
            host='retail-chatbot-db.c0d6e6o2ahcp.us-east-1.rds.amazonaws.com',
            user='admin',
            password='Pavan1845',
            database='Shoeshop',
            cursorclass=pymysql.cursors.DictCursor
        )

        try:
            with connection.cursor() as cursor:
                # Check if customer already exists
                cursor.execute("SELECT customer_id FROM customers WHERE LOWER(name) = LOWER(%s)", (name,))
                customer = cursor.fetchone()

                if not customer:
                    # Insert a placeholder into customers just to create customer_id (without preferences)
                    cursor.execute(
                        "INSERT INTO customers (name, last_purchase_date) VALUES (%s, NOW())",
                        (name,)
                    )
                    connection.commit()
                    cursor.execute(
                        "SELECT customer_id FROM customers WHERE LOWER(name) = LOWER(%s) ORDER BY customer_id DESC LIMIT 1",
                        (name,)
                    )
                    customer = cursor.fetchone()

                customer_id = customer['customer_id']

                # Insert contact info
                cursor.execute(
                    "INSERT INTO customer_contact (customer_id, email, phone_number) VALUES (%s, %s, %s)",
                    (customer_id, email, phone_number)
                )
                connection.commit()
                logger.info(f"New user {name} registered with contact info.")

        finally:
            connection.close()

        return {
            'response': {
                'actionGroup': action_group,
                'function': function,
                'functionResponse': {
                    'responseBody': {
                        'TEXT': {
                            'body': f"Thanks {name}! You’re successfully registered. Now let’s get your preferences to recommend shoes!"
                        }
                    }
                }
            },
            'messageVersion': message_version
        }

    except Exception as e:
        logger.error("Error in new_user_registration: %s", str(e))
        return {
            'statusCode': HTTPStatus.INTERNAL_SERVER_ERROR,
            'body': 'Internal server error during registration'
        }
