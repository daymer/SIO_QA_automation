def tags(tag_name):
    def tags_decorator(func):
        def func_wrapper(name):
            return "<{0}>{1}</{0}>".format(tag_name, func(name))
        return func_wrapper
    return tags_decorator


def get_text(name):
    return "Hello "+name

print(get_text("John"))


'''
def make_message(text:str):
    text = str(text).rstrip()
    return text


@make_message(result)
'''