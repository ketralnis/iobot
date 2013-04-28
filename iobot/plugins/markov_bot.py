import re
import nltk
from datetime import timedelta
from operator import itemgetter
from random import sample, randint
from markov import Markov
from functools import partial
from iobot.plugins.decorators import plugin_command, plugin_hook, admin_command
QUERY_REGEX = r'^(?P<nick>{})[,:] (?P<message>.*)$'
TIMEOUT = timedelta(seconds=5)

class MarkovThrottle(object):
    def __init__(self, user):
        self.user = user
        self.io_timeout = None
        self.count = 1

class MarkovPlugin(object):
    def __init__(self):
        self.markov = Markov(prefix='irc')
        self.silent = False
        self.dumb = False
        self.throttles = []

    @admin_command
    def silence(self, connection, event):
        self.silent = True

    @admin_command
    def unsilence(self, connection, event):
        self.silent = False

    @admin_command
    def dumb_markov(self, connection, event):
        self.dumb = True

    @admin_command
    def learn_markov(self, connection, event):
        self.dumb = False

    @admin_command
    def flush_brain(self, connection, event):
        connection.logger.info('FLUSHING MARKOV BRAIN!!!')
        self.markov.flush()

    @admin_command
    def set_brain(self, connection, event):
        prefix = event.command_params[0]
        connection.logger.info('SETTING MARKOV BRAIN {prefix: %s}' % prefix)
        self.markov.prefix = prefix

    def is_ignored(self, user):
        t = self.get_throttle(user)
        return t and t.count > 3

    @plugin_hook
    def on_privmsg(self, connection, event):
        user = connection.users[event.nick]
        if self.is_ignored(user):
            connection.logger.warning('IGNORED {nick: %s}' % event.nick)
            self.do_throttle(connection.bot.ioloop, user, timedelta(minutes=1))
            return

        m = re.match(QUERY_REGEX.format(connection.nick), event.text)
        if not self.silent and m:
            tokens = tokenize_line(m.group('message'))
            self.do_reply(connection, event, tokens)
            ioloop = connection.bot.ioloop
            self.do_throttle(ioloop, user)
        elif not m and not self.dumb and not event.command:
            connection.logger.info('Learning {message: %s}' % event.text)
            message = event.text
            tokens = word_tokenize(message)
            self.learn_message(tokens)

    def do_reply(self, connection, event, tokens):
        connection.logger.info('Loading reply {tokens: %s}' % repr(tokens))
        reply = load_reply_from_markov(self.markov, event.nick, tokens)
        if reply:
            connection.reply_with_nick(event, reply)
        else:
            connection.reply_with_nick(event, ('I have nothing to'
                ' say yet. Teach me more!'))

    def do_throttle(self, ioloop, user, timeout=TIMEOUT):
        throttle = self.get_throttle(user)
        if throttle:
            ioloop.remove_timeout(throttle.io_timeout)
            throttle.count += 1
        else:
            throttle = MarkovThrottle(user)
            self.throttles.append(throttle)
        rem_user_thrtl = partial(self.remove_throttle, user)
        throttle.io_timeout = ioloop.add_timeout(timeout, rem_user_thrtl)

    def remove_throttle(self, user):
        for t in list(self.throttles):
            if t.user is user:
                self.throttles.remove(t)

    def get_throttle(self, user):
        for t in self.throttles:
            if t.user is user:
                return t
        else:
            return None

    def learn_message(self, tokens):
        self.markov.add_line_to_index(tokens)

word_pattern = re.compile(r'\w+')
def tokenize_line(line):
    tokens = nltk.word_tokenize(line)
    tokens = untokenize_special_characters(tokens, line)

def untokenize_special_characters(tokens, line):
    repaired_tokens = []
    pos = 0
    while pos < len(tokens):
        token = tokens[pos]
        if (not word_pattern.match(token) and
                not re.search(r'\s%s\s' % token, line)):
            if re.search(r'\s%s' % token, line):
                token = token + tokens[pos + 1]
                repaired_tokens.append(token)
                pos += 2
            elif re.search(r'%s\s' % token, line):
                prev_token = repaired_tokens[-1]
                repaired_tokens[-1] = prev_token + token
                pos += 1
            else:
                prev_token = repaired_tokens[-1]
                repaired_tokens[-1] = prev_token + token
                if len(tokens) > pos + 1:
                    required_tokens[-1] += tokens[pos + 1]
                pos += 2
        else:
            repaired_tokens.append(token)
            pos += 1
    return repaired_tokens

def load_reply_from_markov(markov, nick, tokens):
    tokens.append(nick)
    replies = dict()
    for i in range(100):
        num_rel_terms = randint(0, len(tokens))
        if num_rel_terms != 0:
            rel_terms = sample(tokens, num_rel_terms)
            possible_reply = markov.generate(relevant_terms=rel_terms)
        else:
            possible_reply = markov.generate()
        score = markov.score_for_line(possible_reply)
        replies[tuple(possible_reply)] = score
    reply = max(replies.iteritems(), key=itemgetter(1))[0]
    return ' '.join(reply)

Plugin = MarkovPlugin
