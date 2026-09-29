from lark import Lark

GRAMMER = '''
cron_line = cron_definition, white_space*, command?;
cron_definition = seconds, white_space*, minutes;
seconds = asterisk | digit{2};
asterisk = "*";
digit = "

white_space = " ";
command = "blah";
'''