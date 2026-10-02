def calculate(expression):
    parts = expression.split()

    first_number = int(parts[0])
    operation = parts[1]
    second_number = int(parts[2])

    if operation == "+":
        result = first_number + second_number
    elif operation == "-":
        result = first_number - second_number
    elif operation == "*":
        result = first_number * second_number
    elif operation == "/":
        result = first_number / second_number
        
    return(result)


print(calculate("25 * 4"))
print(calculate("100 / 5"))
print(calculate("10 + 7"))
print(calculate("20 - 8"))