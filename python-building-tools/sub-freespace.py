import subprocess

# Represent the command ls -a /var as a dictionary to use in subprocess.Popen
get_free_space = "df -h / | awk 'NR==2 { print $4 }'"

# Send the stdout and stderr of the process to variables we can use in the script.
fs_stdout, fs_stderr = subprocess.Popen(get_free_space, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()

if (fs_stderr):
	print("An error occurred retrieiving free space.")
else:
	print("The free space is: ", fs_stdout)