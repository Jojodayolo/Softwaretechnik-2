import unittest
import csv

class CsvTestResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_results = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.test_results.append((test.id(), "PASSED"))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.test_results.append((test.id(), "FAILED"))

    def addError(self, test, err):
        super().addError(test, err)
        self.test_results.append((test.id(), "ERROR"))

class CsvTestRunner(unittest.TextTestRunner):
    resultclass = CsvTestResult

    def run(self, test):
        result = super().run(test)
        with open("test_results.csv", "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Test Case", "Result"])
            for test_id, status in result.test_results:
                writer.writerow([test_id, status])
        return result
