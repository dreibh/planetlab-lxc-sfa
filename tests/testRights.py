import unittest
from sfa.trust.rights import *

class TestRight(unittest.TestCase):
   def setUp(self):
      pass

   def testRightInit(self):
      right = Right("embed")
      self.assertEqual(right.kind, "embed")

   def testRightCanPerform(self):
      right = Right("embed")
      self.assertTrue(right.can_perform("getticket"))
      self.assertTrue(not right.can_perform("resolve"))

   def testIsSuperset(self):
      pright = Right("sa")
      cright = Right("embed")
      self.assertTrue(pright.is_superset(cright))
      self.assertTrue(not cright.is_superset(pright))

      pright = Right("embed")
      cright = Right("embed")
      self.assertTrue(pright.is_superset(cright))
      self.assertTrue(cright.is_superset(pright))

      pright = Right("control")
      cright = Right("embed")
      self.assertTrue(not pright.is_superset(cright))
      self.assertTrue(not cright.is_superset(pright))

class TestRights(unittest.TestCase):
    def setUp(self):
        pass

    def testInit(self):
        # create a blank right list
        rightList = Rights()

        # create a right list with "embed" in it
        rightList = Rights(string="embed")

    def testAsString(self):
        rightList = Rights()
        self.assertEqual(rightList.save_to_string(), "")

        rightList = Rights(string="embed")
        self.assertEqual(rightList.save_to_string(), "embed")

        rightList = Rights(string="embed,resolve")
        self.assertEqual(rightList.save_to_string(), "embed,resolve")

    def testCanPerform(self):
        rightList = Rights(string="embed")
        self.assertTrue(rightList.can_perform("getticket"))
        self.assertTrue(not rightList.can_perform("resolve"))

        rightList = Rights(string="embed,resolve")
        self.assertTrue(rightList.can_perform("getticket"))
        self.assertTrue(rightList.can_perform("resolve"))

    def testIsSuperset(self):
        pRights = Rights(string="sa")
        cRights = Rights(string="embed")
        self.assertTrue(pRights.is_superset(cRights))
        self.assertTrue(not cRights.is_superset(pRights))

        pRights = Rights(string="embed")
        cRights = Rights(string="embed")
        self.assertTrue(pRights.is_superset(cRights))
        self.assertTrue(cRights.is_superset(pRights))

        pRights = Rights(string="control")
        cRights = Rights(string="embed")
        self.assertTrue(not pRights.is_superset(cRights))
        self.assertTrue(not cRights.is_superset(pRights))

        pRights = Rights(string="control,sa")
        cRights = Rights(string="embed")
        self.assertTrue(pRights.is_superset(cRights))
        self.assertTrue(not cRights.is_superset(pRights))


if __name__ == "__main__":
    unittest.main()
