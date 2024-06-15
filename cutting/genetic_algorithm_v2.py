import random
import uuid
from collections import Counter

from cutting.plot.draw_cuttings_v2 import draw_cuttings_v2


class NoCuttingPatternException(Exception):
    """
    Custom exception class for situations where a cutting pattern is not available.

    This exception is raised when attempting to retrieve a cutting pattern by its unique identifier (ID),
    but no matching pattern is found in the best or feasible cutting pattern lists.

    :param message: Optional message to provide additional details about the exception.
                    Defaults to "No cutting pattern available."
    :type message: str
    """

    def __init__(self, message="No cutting pattern available."):
        self.message = message
        super().__init__(self.message)


class GeneticAlgorithm:
    def __init__(self,
                 beam_length,
                 element_count,
                 element_lengths,
                 population_size=50,
                 generation_count=100,
                 next_generation_feasible_patterns_percent=0.8,
                 mutation_probability=0.2,
                 ):

        self.beam_length = beam_length
        self.element_count = element_count
        self.element_lengths = element_lengths
        self.population_size = population_size
        self.generation_count = generation_count
        self.next_generation_feasible_patterns_percent = next_generation_feasible_patterns_percent
        self.mutation_probability = mutation_probability
        self.unique_element_lengths = [int(el) for el in Counter(self.element_lengths).keys()]
        self.unique_element_lengths_and_count_dict = dict(Counter(self.element_lengths))
        self.feasible_cut_patterns = []
        self.best_cut_patterns = []
        self.solution_population_1 = []
        self.solution_population_2 = []
        self.solution_population = []
        self.solution_cut_patterns = []
        self.crossed_cut_patterns = []
        self.elite_cut_patterns = []
        self.elite_solution = []

    @staticmethod
    def calculate_fitness(cut_pattern):
        """
        Calculate the fitness of a given cutting pattern.

        :param cut_pattern: Cutting pattern to evaluate.
        :type cut_pattern: dict

        :return: Fitness value for the cutting pattern.
        :rtype: float
        """

        return 1.0 / (cut_pattern["waste"] + 1e-10)

    @staticmethod
    def __generate_unique_id():
        return uuid.uuid4().hex

    @staticmethod
    def __subtract_elements(remaining_elements, values_list, frequency):
        """
        Subtract frequencies of elements from the remaining_elements dictionary.

        :param remaining_elements: Dictionary representing remaining quantities of elements.
        :type remaining_elements: dict

        :param values_list: List of values used for subtraction.
        :type values_list: list

        :param frequency: Number of times to subtract the values from remaining_elements.
        :type frequency: int

        :return: Updated dictionary after subtraction if successful, False otherwise.
        :rtype: dict or bool
        """
        modified_remaining_elements = remaining_elements.copy()

        for key, value in zip(modified_remaining_elements.keys(), values_list):
            modified_remaining_elements[key] -= value * frequency

            # Check if the value after subtraction is less than 0
            if modified_remaining_elements[key] < 0:
                # Restore the previous value
                modified_remaining_elements[key] += value
                return False

        return modified_remaining_elements

    @staticmethod
    def __is_cut_pattern_unique_in_cut_patterns(cut_pattern, cut_patterns):
        """
        Check if a cutting pattern is unique among a given list of cutting patterns.

        The method compares the pattern of the specified cutting pattern with the patterns of existing cutting patterns.
        If the pattern is not present among the seen patterns, it is considered unique.

        :param cut_pattern: Cutting pattern to check for uniqueness.
        :type cut_pattern: dict

        :param cut_patterns: List of existing cutting patterns.
        :type cut_patterns: list

        :return: True if the cutting pattern is unique, False otherwise.
        :rtype: bool
        """
        seen_cutting_patterns = tuple([cutting_pattern['pattern'] for cutting_pattern in cut_patterns])

        if cut_pattern['pattern'] not in seen_cutting_patterns:
            return True

        return False

    @staticmethod
    def __get_cut_pattern_id_by_pattern_in_cut_patterns(new_cutting_pattern, cutting_patterns):
        """
        Get the cutting pattern ID based on its pattern within a collection of cutting patterns.

        :param new_cutting_pattern: The new cutting pattern to check.
        :type new_cutting_pattern: dict

        :param cutting_patterns: Collection of existing cutting patterns.
        :type cutting_patterns: list

        :return: ID of the cutting pattern if it already exists in the collection
            , otherwise return the ID of the new pattern.
        :rtype: str
        """
        seen_cutting_patterns = tuple([cutting_pattern['pattern'] for cutting_pattern in cutting_patterns])

        if new_cutting_pattern['pattern'] not in seen_cutting_patterns:
            return new_cutting_pattern['id']

        return cutting_patterns[seen_cutting_patterns.index(new_cutting_pattern['pattern'])]['id']

    @staticmethod
    def __add_cut_pattern_to_genotype(frequency, cut_pattern, genotype):
        """
        Add the cutting pattern to the genotype and update frequencies.

        This static method updates the genotype by adding the given cutting pattern's frequency
        to the existing frequency if the cutting pattern id already exists in the genotype.
        If the id does not exist, it appends a new tuple representing the cutting pattern to the genotype.

        :param frequency: Frequency of the cutting pattern to be added.
        :type frequency: int
        :param cut_pattern: Cutting pattern to be added to the genotype.
        :type cut_pattern: dict
        :param genotype: Genotype represented as a list of tuples, each containing frequency and cutting pattern id.
        :type genotype: list

        :return: Updated genotype with the added cutting pattern.
        :rtype: list
        """
        # Check if the cutting pattern id already exists in the genotype
        id_exists = any(existing_id == cut_pattern['id'] for _, existing_id in genotype)

        if id_exists:
            # If the id already exists, find its index and update the frequency
            for i, (existing_frequency, existing_id) in enumerate(genotype):
                if existing_id == cut_pattern['id']:
                    genotype[i] = (existing_frequency + frequency, existing_id)
                    break
        else:
            # If the id does not exist, append a new tuple representing the cutting pattern
            genotype.append((frequency, cut_pattern['id']))

        return genotype

    def __is_feasible(self, cut_pattern):
        """
        Check if a given cutting pattern is feasible within the specified beam length.

        Determines if the provided cutting pattern is executable by calculating the total length of the cut pieces
        and checking if it is less than or equal to the length of the beam.

        :param cut_pattern: A representation of a cutting pattern, either as a dictionary or a list.
        :type cut_pattern: dict or list

        :return: True if the cutting pattern is feasible; False otherwise.
        :rtype: bool
        """
        if isinstance(cut_pattern, dict):
            cut_pattern = cut_pattern['pattern']

        total_length = sum(
            length * frequency for length, frequency in zip(self.unique_element_lengths, cut_pattern))

        return total_length <= self.beam_length

    def __generate_cut_pattern(self, stock_size):
        """
        Generate a cutting pattern based on given stock size and constraints.

        The method generates a cutting pattern for a given stock size (beam length) considering the constraints:
        - Randomly shuffles the unique element lengths to eliminate bias towards the first element.
        - Iterates through the shuffled lengths, determining a random frequency for each element.
        - Ensures that the generated cutting pattern is feasible by restricting the frequency based on available
          stock length and the count of each element.

        :param stock_size: Length of the stock material (beam length) for which the cutting pattern is generated.
        :type stock_size: int

        :return: Dictionary representing the generated cutting pattern with unique ID, stock size, pattern, and waste.
        :rtype: dict
        """
        cut_pattern = []
        remaining_beam_length = self.beam_length
        unique_elements_length = self.unique_element_lengths.copy()

        # Randomly shuffle the unique element lengths to eliminate bias
        random.shuffle(unique_elements_length)

        for i in range(len(unique_elements_length)):
            # Generate a random frequency for each unique element within the constraints
            frequency = random.randint(0,
                                       min(self.unique_element_lengths_and_count_dict[unique_elements_length[i]],
                                           remaining_beam_length // unique_elements_length[i]))

            cut_pattern.append(frequency)

            remaining_beam_length -= cut_pattern[i] * unique_elements_length[i]

        cut_pattern_id = GeneticAlgorithm.__generate_unique_id()

        # Order the cutting pattern based on the unique element lengths
        ordered_cut_pattern = []
        for el in self.unique_element_lengths:
            el_idx = unique_elements_length.index(el)
            ordered_cut_pattern.append(cut_pattern[el_idx])

        return {"id": cut_pattern_id,
                "stock_size": stock_size,
                "pattern": ordered_cut_pattern,
                "waste": remaining_beam_length}

    def __demand_driven_generate_cut_pattern(self, remaining_elements):
        """
        Generate a cutting pattern based on the demand for remaining elements.

        This method generates a cutting pattern by prioritizing elements with higher demand, ensuring efficient
        utilization of available stock.
        It calculates the frequency of each element based on demand and remaining stock length.

        :param remaining_elements: Dictionary representing the remaining demand for each element.
        :type remaining_elements: dict

        :return: A cutting pattern generated based on demand.
        :rtype: dict
        """
        # Sorting elements by demand in descending order
        sorted_elements = dict(sorted(remaining_elements.items(), key=lambda x: x[1], reverse=True))

        cutting_pattern_id = self.__generate_unique_id()
        remaining_beam = self.beam_length
        cutting_pattern = [0 for _ in range(len(self.unique_element_lengths))]

        for key, value in sorted_elements.items():
            frequency = 0
            if int(value) > 0:
                frequency = min(remaining_beam // key, value)
                remaining_beam -= frequency * key
            cutting_pattern[self.unique_element_lengths.index(key)] = frequency

        return {"id": cutting_pattern_id,
                "stock_size": self.beam_length,
                "pattern": cutting_pattern,
                "waste": remaining_beam}

    def __update_cut_pattern(self, cut_pattern, new_pattern):
        """
        Update an existing cutting pattern with a new pattern and recalculate the waste.

        The method takes an existing cutting pattern, replaces its pattern with a new one, and recalculates the waste.
        The waste is computed as the difference between the stock size (beam length) and the total length of the
        new cutting pattern.

        :param cut_pattern: Existing cutting pattern to be updated.
        :type cut_pattern: dict

        :param new_pattern: New cutting pattern to replace the existing one.
        :type new_pattern: list

        :return: Updated cutting pattern with a new pattern and recalculated waste.
        :rtype: dict
        """
        total_length = sum(
            length * frequency for length, frequency in zip(self.unique_element_lengths, new_pattern))

        waste = self.beam_length - total_length

        return {
            "id": cut_pattern["id"],
            "stock_size": cut_pattern["stock_size"],
            "pattern": new_pattern,
            "waste": waste
        }

    def __generate_cut_pattern_for_remaining_elements(self, remaining_elements):
        """
        Generate a cutting pattern for remaining elements and check for uniqueness.

        This method generates a cutting pattern based on the demand for remaining elements and ensures that the
            generated pattern is unique among feasible cutting patterns.
        If the pattern is not unique, it retrieves the ID of the existing cutting pattern with the same pattern.

        :param remaining_elements: Dictionary representing the remaining demand for elements.
        :type remaining_elements: dict

        :return: A cutting pattern for remaining elements.
        :rtype: dict
        """
        # Generate a cutting pattern based on demand for remaining elements
        cut_pattern = self.__demand_driven_generate_cut_pattern(remaining_elements)

        # Check for the uniqueness of the generated cutting pattern
        if GeneticAlgorithm.__is_cut_pattern_unique_in_cut_patterns(cut_pattern, self.feasible_cut_patterns):
            # If unique, add it to the list of feasible cutting patterns
            self.feasible_cut_patterns.append(cut_pattern)
        else:
            # If not unique, get the existing cutting pattern's ID
            cut_pattern['id'] = (
                GeneticAlgorithm.__get_cut_pattern_id_by_pattern_in_cut_patterns(cut_pattern,
                                                                                 self.feasible_cut_patterns))

        return cut_pattern

    def __add_cut_pattern_with_random_frequency_to_genotype(self, remaining_elements, cut_pattern):
        """
        Add the given cutting pattern to the genotype and update relevant values.

        This method incorporates the given cutting pattern into the genotype,
            updating frequencies and remaining elements.
        It calculates the appropriate frequency to add the cutting pattern while considering constraints and returns the
            frequency used along with the updated remaining elements.

        :param remaining_elements: Dictionary representing the remaining demand for elements.
        :type remaining_elements: dict
        :param cut_pattern: Cutting pattern to be added to the genotype.
        :type cut_pattern: dict

        :return: A tuple containing the frequency used and the updated remaining elements.
                 If the addition is not feasible, it returns (0, False).
        :rtype: tuple
        """
        # Calculate the length obtained after using the cutting pattern
        cut_pattern_length = self.beam_length - cut_pattern['waste']

        # Calculate the total length of remaining elements
        remaining_elements_length = (
            sum(element_length * frequency for element_length, frequency in remaining_elements.items()))

        # Check if the cutting pattern is sufficient to cover all remaining elements
        if remaining_elements_length == cut_pattern_length:
            frequency = 1
        else:
            max_frequency = float('inf')

            # Iterate through remaining elements and calculate the maximum feasible frequency
            for key, value in remaining_elements.items():
                element_count = cut_pattern['pattern'][self.unique_element_lengths.index(key)]

                if element_count != 0:
                    if value == element_count:
                        max_frequency = 1
                    else:
                        frequency = value // element_count
                        if frequency < max_frequency:
                            max_frequency = frequency

            # Handle cases where max_frequency is infinite or zero
            if max_frequency == float('inf'):
                frequency = 1
            else:
                if max_frequency == 0:
                    return 0, False
                frequency = random.randrange(1, max_frequency + 1)

        # Subtract the elements based on the calculated frequency
        temp = self.__subtract_elements(remaining_elements, cut_pattern['pattern'], frequency)

        if temp:
            # Return the frequency used and the updated remaining elements
            return frequency, temp
        else:
            # Return (0, False) if the addition is not feasible
            return 0, False

    def get_cut_pattern_by_id(self, cut_pattern_id):
        """
        Retrieve a cutting pattern based on its unique identifier (ID).

        Searches through both the best and feasible cutting pattern lists to find a pattern with the specified ID.
        If a matching pattern is found, it is returned; otherwise, a NoCuttingPatternException is raised.

        :param cut_pattern_id: The unique identifier (ID) of the cutting pattern to retrieve.
        :type cut_pattern_id: str

        :return: The cutting pattern with the specified ID.
        :rtype: dict

        :raises NoCuttingPatternException: Raised when no cutting pattern is found with the provided ID.
        """
        for cut_pattern in self.best_cut_patterns:
            if cut_pattern_id == cut_pattern['id']:
                return cut_pattern

        for cut_pattern in self.feasible_cut_patterns:
            if cut_pattern_id == cut_pattern['id']:
                return cut_pattern

        raise NoCuttingPatternException("No cutting pattern is available by the provided ID.")

    def calculate_genotype_waste(self, genotype):
        """
        Calculate the total waste resulting from the cutting patterns represented by a given genotype.

        The waste is calculated by summing the product of the frequency of each cutting pattern and the waste
        associated with that pattern.

        :param genotype: A representation of cutting patterns in the form of [(frequency, pattern_id), ...].
        :type genotype: list(tuple(int, str))

        :return: The total waste resulting from the cutting patterns in the genotype.
        :rtype: float
        """
        return sum([frequency * self.get_cut_pattern_by_id(pattern_id)['waste'] for frequency, pattern_id in genotype])

    def generate_population(self):
        """
        Generate a population of cutting patterns until reaching the desired population size.

        This method uses the '__generate_cut_pattern' method to create cutting patterns and ensures that the population
            adheres to feasibility constraints and uniqueness.
        The maximum achievable size of a unique population within practical time frames is considered
            , and if the iterations exceed a threshold without finding a unique cutting pattern
            , the population size is adjusted accordingly.

        :return: None
        """
        iter_without_unique_pattern = 0

        while len(self.feasible_cut_patterns) < self.population_size:
            if iter_without_unique_pattern > 50:
                print()
                print(
                    f"Maximum size of a unique population achievable in practical time frames "
                    f"is: {len(self.feasible_cut_patterns)}. "
                    f"\nPopulation size has been adjusted to: {len(self.feasible_cut_patterns)}.")
                self.population_size = len(self.feasible_cut_patterns)
                break

            cutting_pattern_dict = self.__generate_cut_pattern(self.beam_length)

            if (self.__is_feasible(cutting_pattern_dict) and
                    GeneticAlgorithm.__is_cut_pattern_unique_in_cut_patterns(cutting_pattern_dict,
                                                                             self.feasible_cut_patterns)):

                iter_without_unique_pattern = 0

                self.feasible_cut_patterns.append(cutting_pattern_dict)
            else:
                iter_without_unique_pattern += 1

    def calculate_best_cut_patterns(self, cut_patterns):
        """
        Calculate the best 10 percent of cutting patterns from a given list of cutting patterns.

        The method sorts feasible patterns by fitness in descending order and iterates through them to find the best
        patterns based on coverage of remaining elements.
        It considers the uniqueness of patterns and ensures that the best patterns cover all remaining elements.
        The final list of best patterns is updated in the 'best_cut_patterns' attribute.

        :param cut_patterns: List of cutting patterns to evaluate.
        :type cut_patterns: list[dict]

        :return: None
        """
        # Sort feasible patterns by fitness in descending order
        sorted_population = sorted(cut_patterns, key=lambda x: GeneticAlgorithm.calculate_fitness(x),
                                   reverse=True)

        # Initialize variables
        best_patterns = []
        # Create a set of element lengths, ensuring unique elements
        remaining_elements = set(self.element_lengths)

        # Iterate through sorted patterns
        for pattern in sorted_population:
            # Extract pattern elements
            pattern_elements = set()
            for length, frequency in zip(self.unique_element_lengths, pattern["pattern"]):
                pattern_elements.update([length] * frequency)

            # Check if the pattern covers any remaining elements
            common_elements = pattern_elements.intersection(remaining_elements)

            if common_elements:
                # If the pattern covers remaining elements, add it to the best patterns
                best_patterns.append(pattern)
                # Remove the covered elements from the list of remaining elements
                remaining_elements -= common_elements

                # Check if all elements are covered
                if not remaining_elements:
                    break

        top_10_percent = int(0.1 * len(sorted_population))

        # Include unique patterns in the top 10% of sorted population
        for cutting_pattern_dict in sorted_population:
            if GeneticAlgorithm.__is_cut_pattern_unique_in_cut_patterns(cutting_pattern_dict, best_patterns):
                best_patterns.append(cutting_pattern_dict)
                if len(best_patterns) >= top_10_percent:
                    break

        # Update the best patterns attribute
        self.best_cut_patterns = best_patterns

    def __calculate_cut_pattern_waste(self, pattern):
        remaining_length = self.beam_length
        for i in range(len(pattern)):
            remaining_length -= pattern[i] * self.unique_element_lengths[i]

        return remaining_length

    def __get_or_generate_cutting_pattern_by_pattern(self, pattern):
        result_cut_pattern = None
        for cut_pattern in self.feasible_cut_patterns + self.best_cut_patterns:
            if cut_pattern.get('pattern') == pattern:
                result_cut_pattern = cut_pattern
                break

        if result_cut_pattern is None:
            result_cut_pattern = \
                {
                    'id': self.__generate_unique_id(),
                    'stock_size': self.beam_length,
                    'pattern': pattern,
                    'waste': self.__calculate_cut_pattern_waste(pattern)
                }
            self.best_cut_patterns.append(result_cut_pattern)

        return result_cut_pattern

    def __generate_solution_population_n(self, n):
        """
        Generate a population of genotypes based on existing cutting patterns.

        This method generates a population of genotypes, each representing a potential solution. It utilizes existing
        cutting patterns to construct the genotypes and adheres to specified constraints.

        :param n: Parameter determining the logic for selecting cutting patterns during genotype construction.
                  If n == 1, only the best cutting pattern is considered initially, otherwise, the logic is adjusted.
        :type n: int

        :return: List of genotypes representing the solution population.
        :rtype: list
        """
        # Initialize variables
        solution_population_n = []

        if n == 1:
            i = 0
        else:
            i = 1

        # Iterate through the desired population size
        for _ in range(self.population_size):
            # Choose the first cutting pattern
            first_cut_pattern_id = random.choice(self.best_cut_patterns)["id"]

            # Initialize remaining elements dictionary and total length of all elements
            remaining_elements = dict(Counter(self.element_lengths))
            all_elements_length = sum(self.element_lengths)

            # Initialize genotype and iteration counter without adding a chromosome
            genotype, iter_without_unique_cut_pattern = [], 0

            # Construct the genotype
            while all_elements_length > 0 and sum(remaining_elements.values()) != 0:
                if i == 0:
                    # Logic for selecting the first cutting pattern
                    first_pattern = self.get_cut_pattern_by_id(first_cut_pattern_id)
                    first_pattern_length = self.beam_length - first_pattern['waste']

                    # Check if the first pattern is feasible
                    if 0 < first_pattern_length <= all_elements_length:
                        frequency, modified_remaining_elements = (
                            self.__add_cut_pattern_with_random_frequency_to_genotype(remaining_elements, first_pattern))

                        if modified_remaining_elements:
                            remaining_elements = modified_remaining_elements
                        else:
                            i += 1
                            continue
                    else:
                        first_cut_pattern_id = random.choice(self.best_cut_patterns)["id"]
                        continue

                    genotype.append((frequency, first_cut_pattern_id))
                    all_elements_length -= frequency * first_pattern_length
                    i += 1

                else:
                    # Logic for selecting subsequent cutting patterns
                    if iter_without_unique_cut_pattern > 4:
                        iter_without_unique_cut_pattern = 0
                        cutting_pattern = self.__generate_cut_pattern_for_remaining_elements(remaining_elements)
                        frequency, modified_remaining_elements = (
                            self.__add_cut_pattern_with_random_frequency_to_genotype(remaining_elements,
                                                                                     cutting_pattern))

                        if modified_remaining_elements:
                            remaining_elements = modified_remaining_elements
                            all_elements_length -= ((self.beam_length - cutting_pattern['waste']) * frequency)
                            genotype = GeneticAlgorithm.__add_cut_pattern_to_genotype(
                                frequency, cutting_pattern, genotype)

                        else:
                            i += 1

                        continue

                    random_cut_pattern_id = random.choice(self.feasible_cut_patterns)['id']

                    if iter_without_unique_cut_pattern > 2:
                        random_cut_pattern_id = random.choice(self.best_cut_patterns)["id"]

                    random_cut_pattern = self.get_cut_pattern_by_id(random_cut_pattern_id)
                    random_cut_pattern_length = self.beam_length - random_cut_pattern['waste']

                    # Check if the random pattern is feasible
                    if 0 < random_cut_pattern_length <= all_elements_length:
                        frequency, modified_remaining_elements = (
                            self.__add_cut_pattern_with_random_frequency_to_genotype(remaining_elements,
                                                                                     random_cut_pattern))

                        if modified_remaining_elements:
                            remaining_elements = modified_remaining_elements
                        else:
                            i += 1
                            iter_without_unique_cut_pattern += 1
                            continue

                    else:
                        i += 1
                        iter_without_unique_cut_pattern += 1
                        continue

                    # Check if the frequency is zero
                    if frequency == 0:
                        i += 1
                        iter_without_unique_cut_pattern += 1
                        continue

                    all_elements_length -= frequency * random_cut_pattern_length
                    genotype = GeneticAlgorithm.__add_cut_pattern_to_genotype(frequency, random_cut_pattern, genotype)

                    i += 1

            # Append the genotype to the solution population if not empty
            if len(genotype) != 0:
                solution_population_n.append(genotype)

        return solution_population_n

    def __create_solution_waste_dict(self):
        solution_waste_dict = {}

        for solution in self.solution_population:
            solution_waste_dict[tuple(solution)] = self.calculate_genotype_waste(solution)

        return solution_waste_dict

    def __select_elite_solution(self):
        solution_waste_dict = self.__create_solution_waste_dict()
        if solution_waste_dict is not None and bool(solution_waste_dict):
            min_waste = min(solution_waste_dict.values())
            elite_solution = min(
                [list(solution) for solution, waste in solution_waste_dict.items() if waste == min_waste]
                , key=lambda x: len(x))

            genotype_pattern = []

            for frequency, pattern_id in elite_solution:
                genotype_pattern.append((frequency, self.get_cut_pattern_by_id(pattern_id)['pattern']))

            self.elite_solution = genotype_pattern

    def generate_solution_population_1(self):
        """
        Generate a solution population using the logic specified for n=1.

        This method generates a solution population using the logic specified for n=1
        in the '__generate_solution_population_n' method.
        It utilizes both 'best_cut_patterns' and 'feasible_cut_patterns' for generating genotypes.
        It clears the existing population and updates it with the newly generated genotypes.

        :return: None
        """
        if len(self.solution_population_1) != 0:
            self.solution_population_1 = []

        self.solution_population_1.extend(self.__generate_solution_population_n(n=1))

    def generate_solution_population_2(self):
        """
        Generate a solution population using the logic specified for n=2.

        This method generates a solution population using the logic specified for n=2
        in the '__generate_solution_population_n' method.
        It only utilizes 'feasible_cut_patterns' for generating genotypes.
        It clears the existing population and updates it with the newly generated genotypes.

        :return: None
        """
        if len(self.solution_population_2) != 0:
            self.solution_population_2 = []

        self.solution_population_2 = self.__generate_solution_population_n(n=2).copy()

    def __combine_elite_solution(self):
        if self.elite_solution:
            elite_solution = []
            for frequency, pattern in self.elite_solution:
                cut_pattern = self.__get_or_generate_cutting_pattern_by_pattern(pattern)
                elite_solution.append((frequency, cut_pattern['id']))

            self.elite_solution = []
            self.solution_population.append(elite_solution.copy())

    def combine_solutions(self):
        """
        Combine the solution populations generated for n=1 and n=2 into a single solution population.

        This method uses the logical union (OR) to merge the solutions from
        solution_population_1 and solution_population_2 into a unified solution_population.

        :return: None
        """
        self.solution_population = self.solution_population_1.copy()
        self.solution_population.extend(self.solution_population_2)
        self.__combine_elite_solution()
        self.__select_elite_solution()

    def extract_solution_patterns(self):
        """
        Extract unique cutting patterns from the combined solution populations.

        This method iterates through the genotypes in the solution_population, extracting cutting patterns used to
        generate the genotypes.
        It ensures that only unique cutting patterns are added to the solution_cut_patterns, preventing duplicates.
        The resulting solution_cut_patterns represent the comprehensive set of unique cutting patterns employed
        in the generation of genotypes.

        :return: None
        """
        seen_cutting_patterns = set()
        for genotype in self.solution_population:
            for i in range(len(genotype)):
                cutting_pattern_id = genotype[i][1]

                cutting_pattern = self.get_cut_pattern_by_id(cutting_pattern_id)
                cutting_pattern_tuple = tuple(cutting_pattern["pattern"])
                if cutting_pattern_tuple not in seen_cutting_patterns:
                    seen_cutting_patterns.add(cutting_pattern_tuple)
                    self.solution_cut_patterns.append(cutting_pattern)

    def __create_child(self, pattern_part_1, pattern_part_2):
        """
        Create a child cutting pattern based on two parent patterns.

        This function takes two parts of parent cutting patterns, combines them to create a new child cutting pattern,
        and calculates the waste for the child.

        :param pattern_part_1: First part of the cutting pattern.
        :type pattern_part_1: list
        :param pattern_part_2: Second part of the cutting pattern.
        :type pattern_part_2: list

        :return: A dictionary representing the child cutting pattern.
        :rtype: dict
        """
        child_pattern = pattern_part_1 + pattern_part_2
        child_waste = self.beam_length - sum(
            length * frequency for length, frequency in zip(self.unique_element_lengths, child_pattern))

        return {
            "id": GeneticAlgorithm.__generate_unique_id(),
            "stock_size": self.beam_length,
            "pattern": child_pattern,
            "waste": child_waste
        }

    def crossover(self):
        """
        Perform crossover operation to generate new cutting patterns.

        This method selects pairs of parent cutting patterns, performs crossover at a random point, and creates two
        children cutting patterns. The resulting patterns are added to the crossed_cut_patterns list if they are not
        duplicates and have non-negative waste.

        :return: None
        """
        seen_pattern_tuples = set()

        for i in range(len(self.solution_cut_patterns)):
            # Select two parents for crossover
            parent_1 = self.best_cut_patterns[random.randrange(len(self.best_cut_patterns))]
            parent_2 = self.solution_cut_patterns[i]

            # Determine the crossover point
            b = len(parent_1["pattern"]) - 1
            if b == 0:
                b = 1
            crossover_point = random.randint(1, b)

            # Extract parent patterns
            parent_1_pattern = parent_1["pattern"]
            parent_2_pattern = parent_2["pattern"]

            # Create two children patterns using crossover
            child_1 = self.__create_child(parent_1_pattern[:crossover_point], parent_2_pattern[crossover_point:])
            child_2 = self.__create_child(parent_2_pattern[:crossover_point], parent_1_pattern[crossover_point:])

            # Check for duplicates based on pattern tuples
            child_1_tuple = tuple(child_1["pattern"])
            child_2_tuple = tuple(child_2["pattern"])

            # Add child patterns to the crossed_cut_patterns list if they are not duplicates and have non-negative waste
            if child_1_tuple not in seen_pattern_tuples:
                seen_pattern_tuples.add(child_1_tuple)
                if child_1["waste"] >= 0:
                    self.crossed_cut_patterns.append(child_1)

            if child_2_tuple not in seen_pattern_tuples:
                seen_pattern_tuples.add(child_2_tuple)
                if child_2["waste"] >= 0:
                    self.crossed_cut_patterns.append(child_2)

    def select_elitism(self):
        """
        Select elite cutting patterns based on fitness.

        Sorts the feasible_cut_patterns based on their fitness values and selects patterns with the best fitness.
        The elite_cut_patterns list is updated with the selected patterns.

        :return: None
        """
        # Sort feasible patterns by fitness in descending order
        sorted_patterns = sorted(self.feasible_cut_patterns, key=lambda x: GeneticAlgorithm.calculate_fitness(x),
                                 reverse=True)

        # Get the best fitness value
        best_fitness = GeneticAlgorithm.calculate_fitness(sorted_patterns[0])

        # Select elite cutting patterns with the best fitness
        self.elite_cut_patterns.extend([
            pattern for pattern in sorted_patterns if GeneticAlgorithm.calculate_fitness(pattern) == best_fitness
        ])

    def update_cut_patterns(self):
        """
        Update cutting patterns by combining elite patterns, crossed patterns, and selecting the best feasible patterns.

        Combines elite patterns and crossed patterns, sorts feasible patterns, selects the top patterns based
        on the specified percentage, and updates feasible_cut_patterns. Finally, it calculates the best cut patterns.

        :return: None
        """
        # Combine elite patterns and crossed patterns
        combined_cut_patterns = self.crossed_cut_patterns.copy()
        for elite_cut_pattern in self.elite_cut_patterns:
            if GeneticAlgorithm.__is_cut_pattern_unique_in_cut_patterns(elite_cut_pattern, combined_cut_patterns):
                combined_cut_patterns.append(elite_cut_pattern)

        # Sort cutting patterns by waste value
        sorted_cut_patterns = sorted(self.feasible_cut_patterns, key=lambda x: x["waste"])

        # Calculate the index from which to start selecting patterns (% of the best)
        selection_index = int(len(sorted_cut_patterns) * self.next_generation_feasible_patterns_percent)

        # Select the best feasible cutting patterns
        selected_patterns = sorted_cut_patterns[:selection_index]
        self.feasible_cut_patterns = selected_patterns.copy()

        # Combine elite patterns and feasible patterns
        cutting_patterns = self.best_cut_patterns.copy()
        cutting_patterns.extend(self.feasible_cut_patterns)

        # Calculate the best cut patterns
        self.calculate_best_cut_patterns(cutting_patterns)

    def mutate(self, cut_patterns):
        """
        Mutate the given cutting patterns.

        This method mutates cutting patterns by randomly incrementing individual elements in the pattern.
        It ensures that the mutated pattern remains feasible.

        :param cut_patterns: List of cutting patterns to be mutated.
        :type cut_patterns: list

        :return: List of mutated cutting patterns.
        :rtype: list
        """
        mutated_cut_patterns = []

        for cut_pattern in cut_patterns:
            mutated_pattern = cut_pattern['pattern'].copy()

            for i in range(len(mutated_pattern)):
                # Check if mutation should occur for the current element
                if random.random() < self.mutation_probability:
                    # Increment the selected element until the pattern remains feasible
                    original_element = mutated_pattern[i]

                    # Check if the original element can be incremented
                    if original_element < self.unique_element_lengths[i]:
                        mutated_element = original_element + 1
                        mutated_pattern[i] = mutated_element
                        if not self.__is_feasible(mutated_pattern):
                            mutated_pattern[i] = original_element
                            continue

                        while mutated_element <= self.unique_element_lengths[i] and not self.__is_feasible(
                                mutated_pattern):
                            mutated_pattern[i] = mutated_element
                            mutated_element += 1
                        break

            mutated_cut_patterns.append(self.__update_cut_pattern(cut_pattern, mutated_pattern))

        return mutated_cut_patterns.copy()

    def choose_the_best(self):
        """
        Choose the best genotype from the solution population considering both waste and the minimum number of unique
        cutting patterns used.

        This method selects the best genotype based on a combination of waste produced and the minimum number
        of unique cutting patterns used. It returns the corresponding cutting patterns.

        :return: A tuple containing the best genotype represented as a list of tuples (frequency, cutting pattern ID),
                 and the cutting patterns corresponding to the best result.
        :rtype: tuple
        """

        solution_waste_dict = self.__create_solution_waste_dict()
        min_waste = min(solution_waste_dict.values())
        best_solution = min(
            [list(solution) for solution, waste in solution_waste_dict.items() if waste == min_waste]
            , key=lambda x: len(x))

        # Retrieve cutting patterns corresponding to the best result
        best_chromosomes = [self.get_cut_pattern_by_id(chromosome[1]) for chromosome in best_solution]

        return best_solution, best_chromosomes

    def draw_cuttings(self, genotype, chromosomes, genotype_waste):
        """
        Visualize the cuttings based on the given genotype and cutting patterns.

        This method utilizes the draw_cuttings function to visualize the cuttings based on the provided genotype and
        cutting patterns.

        :param genotype_waste:
        :param genotype: Genotype represented as a list of tuples, each containing frequency and cutting pattern ID.
        :type genotype: list
        :param chromosomes: List of cutting patterns corresponding to the genotype.
        :type chromosomes: list
        :return: uri with encode plot in base64 for showing on front-end
        """
        return draw_cuttings_v2(genotype=genotype,
                                chromosomes=chromosomes,
                                unique_elements_length_dict=self.unique_element_lengths_and_count_dict,
                                genotype_waste=genotype_waste)

    def run(self):
        """
        Execute the genetic algorithm to find the optimal solution.

        This method runs the genetic algorithm for the specified number of generations, following the defined steps:

        (1) Generate the initial population of cutting patterns.
        (2-3) Calculate the best cutting patterns based on feasibility.
        (4-5) Generate solution populations for n=1 and n=2.
        (6) Combine the solution populations.
        (7) Extract cutting patterns from the combined solutions.
        (8) Perform crossover to generate new cutting patterns.
        (9) Select the elite cutting patterns.
        (10) Update the set of feasible cutting patterns.
        (11) Mutate the best and feasible cutting patterns.

        The process is repeated for the specified number of generations, and the best solution is chosen based on waste
        and the minimum number of unique cutting patterns used.

        :return: A tuple containing the best solution and the cutting patterns for the best solution.
        :rtype: tuple
        """
        self.generate_population()  # (1)
        self.calculate_best_cut_patterns(self.feasible_cut_patterns)  # (2-3)

        for i in range(self.generation_count - 1):
            self.generate_solution_population_1()  # (4)
            self.generate_solution_population_2()  # (5)
            self.combine_solutions()  # (6)
            self.extract_solution_patterns()  # (7)
            self.crossover()  # (8)
            self.select_elitism()  # (9)
            self.update_cut_patterns()  # (10)
            self.best_cut_patterns = self.mutate(self.best_cut_patterns)  # (11)
            self.feasible_cut_patterns = self.mutate(self.feasible_cut_patterns)  # (11)

        # Additional iterations without mutation for choosing the best solution
        self.generate_solution_population_1()  # (4)
        self.generate_solution_population_2()  # (5)
        self.combine_solutions()  # (6)
        self.extract_solution_patterns()  # (7)
        self.crossover()  # (8)
        self.select_elitism()  # (9)
        self.update_cut_patterns()  # (10)

        # Final iteration for choosing the best solution
        self.generate_solution_population_1()  # (4)
        self.generate_solution_population_2()  # (5)
        self.combine_solutions()  # (6)

        best_solution, cutting_patterns_for_best_solution = self.choose_the_best()

        return (best_solution,
                cutting_patterns_for_best_solution,
                self.calculate_genotype_waste(best_solution),
                self.unique_element_lengths_and_count_dict)
