from without_langchain import queryyy 

# https://medium.com/artificial-corner/re-ranking-is-all-you-need-7a6b1e586d48
def start():
    instructions = (
        """How can I help you today ?\n"""
    )

    print("MENU")
    print("====")
    print("[1]- Ask a question")
    print("[2]- Exit")
    choice = input("Enter your choice: ")
    if choice == "1":
        ask()
    elif choice == "2":
        print("Goodbye!")
        exit()
    else:
        print("Invalid choice")
        start()


def ask():
    while True:
        user_input = input("Q: ")
        # Exit
        if user_input == "x":
            start()
        else:

            response = queryyy(user_input)
            print(response)
            print( "\n-------------------------------------------------")


if __name__ == "__main__":
    start()
