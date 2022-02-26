#!/usr/bin/env python3
# Copyright 2009-2017 BHG http://bw.org/

secret = 'swordfish'
pw = ''
auth = False
tries = 0
max_tries = 5

while pw != secret:
    tries += 1
    if tries > max_tries: break

    pw = input("What's the secret word? ")
    
else:
    auth = True

print("Authorized" if auth else "busted!")
