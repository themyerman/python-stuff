import traceback

try:
	i = 10
	j = i/0

except ZeroDivisionError:
	traceback.print_exc()

print("Program proceeds!")