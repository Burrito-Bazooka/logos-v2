# tests

# Import the plugin you wish to test
from plugins.bible.plugin import BibleBot

# Subclass your test class from LogosTestCase
from bot.testing.utils import LogosTestCase

class TestBibleBot(LogosTestCase):
    # set plugin_class to the actual class
    # of the plugin you wish to test
    plugin_class = BibleBot
    
    def testVerseLookup(self):
        
        output = self.plugin.send_command("John 3 16")
        self.assertIn('John 3:16', output)
        
        output = self.plugin.send_command("next")
        self.assertIn('John 3:17', output)
        
        # Test the parser works with embedded spaces
        output = self.plugin.send_command("col 1 :18")
        self.assertIn('Colossians 1:18', output)
        
        output = self.plugin.send_command("col 1: 18")
        self.assertIn('Colossians 1:18', output)
        
        # Test the search works with different Nicks
        self.set_nick("Fred")
        output = self.plugin.send_command("search kjv Jesus wept")
        self.assertIn('John 11:35', output)
        
        self.set_nick("Jake")
        output = self.plugin.send_command("search kjv Jesus wept")
        self.assertIn('John 11:35', output)

        

        
        