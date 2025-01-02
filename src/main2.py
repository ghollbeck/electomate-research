# # main.py

# import logging
# from langchain_core.runnables import RunnableConfig
# from gpt_interface2 import get_graph, initial_state

# if __name__ == "__main__":
#     # Load environment variables if needed
#     import dotenv
#     dotenv.load_dotenv(dotenv_path='src/.env')

#     # Configure logging to see the pipeline's progress
#     logging.basicConfig(
#         level=logging.INFO, 
#         format='%(asctime)s - %(levelname)s - %(message)s'
#     )

#     # Instantiate the pipeline
#     app = get_graph()

#     # Create a RunnableConfig with recursion limit, if desired
#     config = RunnableConfig(recursion_limit=10)

#     # Define the question we want to ask
#     question_input = "What is the economic policy approach of the CDU in Germany?"

#     # Provide instructions if recursion limit is reached
#     preamble = (
#         "Our algorithm has reached our self-imposed recursion limit of 10. "
#         "We are not confident enough that the data in the context is sufficient to answer your question, "
#         "but we will still provide the best possible answer given the data:\n\n"
#     )

#     # Run the pipeline and print out each node's output
#     try:
#         for output in app.stream({'question': question_input}, config=config):
#             # Logs (keys and values at each step)
#             for key, value in output.items():
#                 logging.info(f"Node: {key} => {value}")
#         # After the final iteration, the pipeline's last node has "generation"
#         # The final 'value' in the loop is the last step's dictionary
#         print("\nFinal Answer:\n", value["generation"])

#     except Exception as e:
#         # If recursion limit or other error occurs, output a fallback
#         print(preamble)
#         if 'value' in locals() and isinstance(value, dict) and "generation" in value:
#             print(value["generation"])
#         else:
#             print("No valid generation found. Error:", e)


# main.py

import logging
from langchain_core.runnables import RunnableConfig
from graph_app import get_graph, initial_state

if __name__ == "__main__":
    # Load environment variables if needed
    import dotenv
    dotenv.load_dotenv(dotenv_path='src/.env')

    # Configure logging to see the pipeline's progress
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Instantiate the pipeline
    app = get_graph()

    # Create a RunnableConfig with recursion limit, if desired
    config = RunnableConfig(recursion_limit=10)

    # Define the question we want to ask
    question_input = "What is the economic policy approach of the CDU in Germany?"

    # Provide instructions if recursion limit is reached
    preamble = (
        "Our algorithm has reached our self-imposed recursion limit of 10. "
        "We are not confident enough that the data in the context is sufficient to answer your question, "
        "but we will still provide the best possible answer given the data:\n\n"
    )

    # Run the pipeline and print out each node's output
    try:
        for output in app.stream({'question': question_input}, config=config):
            # Logs (keys and values at each step)
            for key, value in output.items():
                logging.info(f"Node: {key} => {value}")
        # After the final iteration, the pipeline's last node has "generation"
        # The final 'value' in the loop is the last step's dictionary
        print("\nFinal Answer:\n", value["generation"])

    except Exception as e:
        # If recursion limit or other error occurs, output a fallback
        print(preamble)
        if 'value' in locals() and isinstance(value, dict) and "generation" in value:
            print(value["generation"])
        else:
            print("No valid generation found. Error:", e)