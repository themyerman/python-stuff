import sys
print(sys.version)
import os

print("GETCWD %s" % os.getcwd())
print("PID %d" % os.getpid())
print("GETUID %d" % os.getuid())
print("UNAME %s" % os.uname()[1]) #its a list!
print(os.listdir(os.getcwd()))
os.mkdir("foo")
print("FOO EXIST? %s" % os.path.exists("foo"))
print(os.listdir(os.getcwd()))
os.rmdir("foo")
print(os.listdir(os.getcwd()))
print("FOO EXIST? %s" % os.path.exists("foo"))
