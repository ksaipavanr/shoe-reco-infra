# import logging
import re
from typing import Dict, Any
from http import HTTPStatus
import pymysql

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def extract_numeric_value(value: str) -> float:
    """Extract numeric value from user input like '100 dollars' or 'below 2000'"""
    match = re.search(r'\d+(?:\.\d+)?', value)
    if match:
        return float(match.group())
    raise ValueError(f"Could not extract numeric value from: {value}")

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        action_group = event['actionGroup']
        function = event['function']
        message_version = event.get('messageVersion', 1)
        parameters = event.get('parameters', [])

        param_map = {param['name'].lower(): param['value'] for param in parameters}
        name = param_map.get('name')
        shoe_size = param_map.get('shoe_size')
        activity_type = param_map.get('activity_type')
        shoe_color = param_map.get('shoe_color')
        price_limit = param_map.get('price_limit')  # New parameter

        logger.info('Received parameters: %s', param_map)

        if price_limit:
            try:
                price_limit = extract_numeric_value(price_limit)
            except ValueError as e:
                logger.error('Invalid price input: %s', e)
                return {
                    'response': {
                        'actionGroup': action_group,
                        'function': function,
                        'functionResponse': {
                            'responseBody': {
                                'TEXT': {
                                    'body': "I couldn’t understand the price you mentioned. Please specify a number like 'below 2000 rupees'."
                                }
                            }
                        }
                    },
                    'messageVersion': message_version
                }

        connection = pymysql.connect(
            host='retail-chatbot-db.c0d6e6o2ahcp.us-east-1.rds.amazonaws.com',
            user='admin',
            password='Pavan1845',
            database='Shoeshop',
            cursorclass=pymysql.cursors.DictCursor
        )

        try:
            with connection.cursor() as cursor:
                customer_found = False

                if name:
                    # Check if customer already exists
                    sql_check = "SELECT activity_type, shoe_size, shoe_color_preference FROM customers WHERE LOWER(name) = LOWER(%s) LIMIT 1"
                    cursor.execute(sql_check, (name,))
                    customer = cursor.fetchone()
                    logger.info('Customer record: %s', customer)

                    if customer:
                        customer_found = True
                        # Use existing data if available
                        activity_type = activity_type or customer['activity_type']
                        shoe_size = shoe_size or customer['shoe_size']
                        shoe_color = shoe_color or customer['shoe_color_preference']
                    else:
                        # New user, ask for traits
                        missing_traits = []
                        if not activity_type:
                            missing_traits.append("preferred activity")
                        if not shoe_size:
                            missing_traits.append("shoe size")
                        if not shoe_color:
                            missing_traits.append("shoe color")

                        if missing_traits:
                            missing_text = ", ".join(missing_traits)
                            response_body = {
                                'TEXT': {
                                    'body': f"Hi {name}, could you tell me your {missing_text} so I can recommend the perfect shoes for you?"
                                }
                            }
                            return {
                                'response': {
                                    'actionGroup': action_group,
                                    'function': function,
                                    'functionResponse': {
                                        'responseBody': response_body
                                    }
                                },
                                'messageVersion': message_version
                            }

                        # Insert new customer
                        sql_insert = """
                        INSERT INTO customers (name, activity_type, shoe_size, shoe_color_preference, last_purchase_date)
                        VALUES (%s, %s, %s, %s, NOW())
                        """
                        cursor.execute(sql_insert, (name, activity_type, shoe_size, shoe_color))
                        connection.commit()
                        logger.info(f"New customer added: {name}")

                # Build dynamic query for shoes
                conditions = []
                values = []

                if activity_type:
                    conditions.append("suitable_for = %s")
                    values.append(activity_type)
                if shoe_size:
                    conditions.append("size = %s")
                    values.append(shoe_size)
                if shoe_color:
                    conditions.append("color = %s")
                    values.append(shoe_color)
                if price_limit:
                    conditions.append("price <= %s")
                    values.append(price_limit)

                sql_shoes = "SELECT shoe_id, shoe_type, shoe_style, color, size, price FROM shoes"
                if conditions:
                    sql_shoes += " WHERE " + " AND ".join(conditions)

                cursor.execute(sql_shoes, tuple(values))
                shoes = cursor.fetchall()
                logger.info('Matching shoes: %s', shoes)

                if shoes:
                    shoe_list = ""
                    for shoe in shoes[:3]:
                        shoe_list += (
                            f"[Shoe ID {shoe['shoe_id']}] "
                            f"{shoe['shoe_type']} {shoe['shoe_style']} – "
                            f"{shoe['color']} – ₹{shoe['price']}\n"
                        )

                    response_body = {
                        'TEXT': {
                            'body': f"Hi {name}! Based on your preferences, here are some shoes you might like:\n{shoe_list}"
                        }
                    }
                else:
                    response_body = {
                        'TEXT': {
                            'body': f"Sorry {name}, I couldn't find shoes matching your preferences right now."
                        }
                    }

        finally:
            connection.close()

        return {
            'response': {
                'actionGroup': action_group,
                'function': function,
                'functionResponse': {
                    'responseBody': response_body
                }
            },
            'messageVersion': message_version
        }

    except KeyError as e:
        logger.error('Missing required field: %s', str(e))
        return {
            'statusCode': HTTPStatus.BAD_REQUEST,
            'body': f'Error: {str(e)}'
        }
    except Exception as e:
        logger.error('Unexpected error: %s', str(e))
        return {
            'statusCode': HTTPStatus.INTERNAL_SERVER_ERROR,
            'body': 'Internal server error'
        }