import thread
def helloWorld(name):
	print("Thread name: %s" % (threadName,))

thread.start_new_thread(helloWorld, ("foo",))
thread.start_new_thread(helloWorld, ("bar",))
thread.start_new_thread(helloWorld, ("baz",))
