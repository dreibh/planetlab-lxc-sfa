# Matches and targets are specified using XML files.
# They provide the following information:
#   - The context required by the match
#   - The processor that actually implements the match or target
#   - The parameters that the processor needs to evaluate the context

import libxml2

class Xmlextension:
    def __init__(self, file_path):

        self.context = ""
        self.processor = ""
        self.operand = "VALUE"
        self.arguments = []
        self.terminal = 0

        self.xmldoc = libxml2.parseFile(file_path)

        # TODO: Check xmldoc against a schema
        p = self.xmldoc.xpathNewContext()

        # <context select="..."/>
        # <rule><argument param="..."/></rule>
        # <processor name="..."/>

        context = p.xpathEval('//context/@select')
        self.context = context[0].content

        processor = p.xpathEval('//processor/@filename')
        self.context = processor[0].content

        name = p.xpathEval('//rule/argument/name')
        help = p.xpathEval('//rule/argument/help')
        target = p.xpathEval('//rule/argument/operand')

        context = p.xpathEval('//attributes/attribute[@terminal="yes"]')
        self.terminal = (context != [])

        self.arguments = [{'name':name_help_target[0].content,'help':name_help_target[1].content,'target':name_help_target[2].content} for name_help_target in zip(name,help,target)]
        
        p.xpathFreeContext()
        self.xmldoc.freeDoc()

        return

