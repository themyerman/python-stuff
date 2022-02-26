#!/usr/bin/env python3
# Copyright 2009-2017 BHG http://bw.org/

class Duck:
    sound = "quackkkkkk"
    movement = 'walks like a duck!'
    say = "I am rich!"

    def quack(self):
        print(self.sound)

    def walk(self):
        print(self.movement)

    def says(self):
        print(self.say)

def main():
    donald = Duck()
    donald.quack()
    donald.walk()

    scrooge = Duck()
    scrooge.says()

if __name__ == '__main__': main()
