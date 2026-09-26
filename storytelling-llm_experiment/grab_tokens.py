import tiktoken

# This grabs the exact tokenizer used by GPT-4o
encoder = tiktoken.encoding_for_model("gpt-4o")

# Your target words, both standard and space-prefixed
target_words = [
    "kyrop", " kyrop", "kyrop", "kyrop ", " kyrop", "kyrop ", " kirrop",
    "doh-bane", " doh-bane", "doh-bane ", "doh-bane", " doh-bane", "doh-bane ",
    "guyg-in", " guyg-in", "guyg-in ","guyg-in", " guyg-in", "guyg-in ", "gig"
    "balides", " balides", "balides ", " Balides", "Balides ", "Balides",
    "tay-tot", " tay-tot", "tay-tot ", "tay-tot", " tay-tot", "tay-tot ", "tay"
]

banned_dict = {}

for word in target_words:
    # Encode the word into token IDs
    tokens = encoder.encode(word)

    # Grab just the FIRST token of the word to stop it from starting
    first_token_id = str(tokens[0])

    # Add it to our dictionary with a -100 ban
    banned_dict[first_token_id] = -100

print("Your logit_bias dictionary:")
print(banned_dict)