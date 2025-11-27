# import logging
from typing import Dict, Any
from http import HTTPStatus
import pymysql
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Amazon SES client
ses_client = boto3.client('ses', region_name='us-east-1')  # Replace with your SES region

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        action_group = event['actionGroup']
        function = event['function']
        message_version = event.get('messageVersion', 1)
        parameters = event.get('parameters', [])

        # Extract parameters
        customer_input = None
        shoe_id = None
        operation = None

        for param in parameters:
            if param['name'] == 'customer_id':
                customer_input = param['value']
            elif param['name'] == 'shoe_id':
                try:
                    shoe_id = int(param['value'])
                except (ValueError, TypeError):
                    shoe_id = None
            elif param['name'] == 'operation':
                operation = param['value'].lower()

        if not customer_input or not operation:
            raise KeyError("Missing required parameter: customer_id or operation")

        logger.info(f"Received parameters: customer_input={customer_input}, shoe_id={shoe_id}, operation={operation}")

        # Connect to DB
        connection = pymysql.connect(
            host='retail-chatbot-db.c0d6e6o2ahcp.us-east-1.rds.amazonaws.com',
            user='admin',
            password='Pavan1845',
            database='Shoeshop'
        )

        try:
            with connection.cursor() as cursor:
                # Resolve customer_id if name is passed
                try:
                    customer_id = int(customer_input)
                except ValueError:
                    cursor.execute("SELECT customer_id FROM customers WHERE name = %s", (customer_input,))
                    result = cursor.fetchone()
                    if result:
                        customer_id = result[0]
                    else:
                        raise ValueError(f"No customer found with name {customer_input}")

                if operation == "create" and shoe_id:
                    # Insert order
                    cursor.execute("""
                        INSERT INTO orders (customer_id, shoe_id, order_date)
                        VALUES (%s, %s, now())
                    """, (customer_id, shoe_id))
                    connection.commit()
                    logger.info("Order inserted successfully.")

                    # Fetch customer details
                    cursor.execute("""
                        SELECT name, activity_type, shoe_size, shoe_color_preference, last_purchase_date
                        FROM customers
                        WHERE customer_id = %s
                    """, (customer_id,))
                    customer = cursor.fetchone()

                    # Fetch shoe details
                    cursor.execute("""
                        SELECT shoe_type, shoe_style, color, size, price, suitable_for
                        FROM shoes
                        WHERE shoe_id = %s
                    """, (shoe_id,))
                    shoe = cursor.fetchone()

                    if customer and shoe:
                        # Compose email
                        recipient_email = "ksaipavanr45@gmail.com"  # Replace with your verified email
                        subject = "Your Shoe Order Confirmation"
                        body = f"""
Hello {customer[0]},

Thank you for your order! Here are the details:

Customer:
- Name: {customer[0]}
- Activity Type: {customer[1]}
- Preferred Size: {customer[2]}
- Color Preference: {customer[3]}
- Last Purchase: {customer[4]}

Shoe:
- Type: {shoe[0]}
- Style: {shoe[1]}
- Color: {shoe[2]}
- Size: {shoe[3]}
- Price: ${shoe[4]}
- Suitable For: {shoe[5]}

We appreciate your business!

Thanks,
Retail Shoe Store
"""

                        # Send email
                        ses_client.send_email(
                            Source="ksaipavanr@gmail.com",  # Must be verified in SES
                            Destination={"ToAddresses": [recipient_email]},
                            Message={
                                "Subject": {"Data": subject},
                                "Body": {"Text": {"Data": body}}
                            }
                        )

                        logger.info(f"Email sent to {recipient_email}")

                    response_body = {
                        'TEXT': {
                            'body': f"Order placed successfully and confirmation sent to {recipient_email}!"
                        }
                    }

                elif operation == "fetch":
                    cursor.execute("""
                        SELECT shoe_id, order_date FROM orders
                        WHERE customer_id = %s
                        ORDER BY order_date DESC
                        LIMIT 10
                    """, (customer_id,))
                    results = cursor.fetchall()
                    if results:
                        order_lines = [
                            f"Shoe ID {row[0]} on {row[1].strftime('%Y-%m-%d')}"
                            for row in results
                        ]
                        history_text = "Here are your past orders:\n" + "\n".join(order_lines)
                    else:
                        history_text = "No past orders found for your profile."

                    response_body = {
                        'TEXT': {
                            'body': history_text
                        }
                    }

                else:
                    raise ValueError("Invalid operation or missing parameters.")

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
            'body': f'Internal server error: {str(e)}'
        }