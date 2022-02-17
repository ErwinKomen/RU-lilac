# Natural Language Toolkit: Tokenizer Interface
#
# Copyright (C) 2001-2020 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Tokenizer Interface
"""

from abc import ABC, abstractmethod

from . util import string_span_tokenize

######################################################################
# Check if a method has been overridden
######################################################################


def overridden(method):
    """
    :return: True if ``method`` overrides some method with the same
    name in a base class.  This is typically used when defining
    abstract base classes or interfaces, to allow subclasses to define
    either of two related methods:

        >>> class EaterI:
        ...     '''Subclass must define eat() or batch_eat().'''
        ...     def eat(self, food):
        ...         if overridden(self.batch_eat):
        ...             return self.batch_eat([food])[0]
        ...         else:
        ...             raise NotImplementedError()
        ...     def batch_eat(self, foods):
        ...         return [self.eat(food) for food in foods]

    :type method: instance method
    """
    if isinstance(method, types.MethodType) and method.__self__.__class__ is not None:
        name = method.__name__
        funcs = [
            cls.__dict__[name]
            for cls in _mro(method.__self__.__class__)
            if name in cls.__dict__
        ]
        return len(funcs) > 1
    else:
        raise TypeError("Expected an instance method.")


class TokenizerI(ABC):
    """
    A processing interface for tokenizing a string.
    Subclasses must define ``tokenize()`` or ``tokenize_sents()`` (or both).
    """

    @abstractmethod
    def tokenize(self, s):
        """
        Return a tokenized copy of *s*.

        :rtype: list of str
        """
        if overridden(self.tokenize_sents):
            return self.tokenize_sents([s])[0]

    def span_tokenize(self, s):
        """
        Identify the tokens using integer offsets ``(start_i, end_i)``,
        where ``s[start_i:end_i]`` is the corresponding token.

        :rtype: iter(tuple(int, int))
        """
        raise NotImplementedError()

    def tokenize_sents(self, strings):
        """
        Apply ``self.tokenize()`` to each element of ``strings``.  I.e.:

            return [self.tokenize(s) for s in strings]

        :rtype: list(list(str))
        """
        return [self.tokenize(s) for s in strings]

    def span_tokenize_sents(self, strings):
        """
        Apply ``self.span_tokenize()`` to each element of ``strings``.  I.e.:

            return [self.span_tokenize(s) for s in strings]

        :rtype: iter(list(tuple(int, int)))
        """
        for s in strings:
            yield list(self.span_tokenize(s))


class StringTokenizer(TokenizerI):
    """A tokenizer that divides a string into substrings by splitting
    on the specified string (defined in subclasses).
    """

    @property
    @abstractmethod
    def _string(self):
        raise NotImplementedError

    def tokenize(self, s):
        return s.split(self._string)

    def span_tokenize(self, s):
        for span in string_span_tokenize(s, self._string):
            yield span
