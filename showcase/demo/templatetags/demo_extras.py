from django.template import Library, Node, Context

register = Library()


class CodeListingNode(Node):
    def __init__(self, content):
        self.content = content

    def render(self, context):
        return self.content.replace("<", "&lt;").replace(">", "&gt;")


@register.tag
def codelisting(parser, token):
    """
    Stop the template engine from rendering the contents of this block tag.
    and escape html tags
    """
    nodelist = parser.parse(("endcodelisting",))
    parser.delete_first_token()
    return CodeListingNode(nodelist.render(Context()))
