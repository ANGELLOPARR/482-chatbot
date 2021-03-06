To start the bot and connect it to an IRC channnel, run the
command below from the command line after pip installing all required packages
<channel-name> is the name of a desired channel (no pound sign)
make sure to include the quotes around the # + channel name

python3 testbot.py irc.freenode.net "#<channel-name>" nutrition

To run commands from the creative part of my chatbot you can make 2 types of inquiries:

1)
How much/many _______ are in [a] __________?
               <FIELD>             <FOOD>

You can use much or many in this phrase and you can include an additional a/an 
to refer to a singular food. The first blank refers to the field of the nutrition
label you want and the second blank is the food.

ex.:

How much fiber is in a banana?

2)

Tell me about _______

The underline in this is a food, and this will give you general, important facts
about the food specified

ex.:

Tell me about bananas