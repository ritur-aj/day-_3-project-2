# Height-Based Ride Ticket Calculator 🎢

A beginner-friendly Python project that calculates a ride ticket price using a visitor's height and age. It also includes an optional photo add-on.

## Features

- Accepts the visitor's age.
- Converts height from feet to centimeters when `ft` is selected.
- Checks whether the visitor meets the minimum height requirement of **more than 120 cm**.
- Calculates the ticket price based on age.
- Adds a photo fee of **$3** in the intended flow.
- Displays the height in centimeters and the total price.

## Ticket Pricing

| Visitor's age | Ride ticket price |
|---|---:|
| Under 12 | $5 |
| 12–17 | $7 |
| 18–44 | $12 |
| 45 and older | $0 |

**Height requirement:** The visitor must be taller than 120 cm to ride.

**Photo add-on:** $3 (intended to be charged only when the visitor chooses a photo).

## Requirements

- Python 3
- No external libraries are required.

## How to Run

1. Save the Python code in a file, for example, `ride_ticket_calculator.py`.
2. Open a terminal or command prompt in the folder containing the file.
3. Run:

   ```bash
   python ride_ticket_calculator.py
   ```

   On some systems, use `python3` instead:

   ```bash
   python3 ride_ticket_calculator.py
   ```

4. Enter the requested unit, age, height, and photo preference when prompted.

## Example

For a visitor who is 20 years old, 5.5 feet tall, and requests a photo:

```text
please choose one unit from (ft / cm) : ft
Enter your Age : 20
enter your height in ft : 5.5
Do you want photo (Yes/No) : Yes
You can ride.
Height = 167.64cm
Your total price for a ride is : $15
```

## Important Notes About the Current Code

The current version has a couple of logic issues to fix before relying on all inputs:

1. **Centimeter input is not handled yet.** The code converts the height only when `ft` is selected. If `cm` is selected, `Height_cm` remains `0`, so the height check will fail. The height prompt should also match the selected unit.
2. **The photo fee condition is always true.** The expression `if Picture == "Yes"or "yes" or "y" or"Y":` evaluates as true regardless of what the user enters, so the $3 photo fee is always added. A safer check is:

   ```python
   if Picture.strip().lower() in ("yes", "y"):
       Total_price += 3
   ```

3. **Visitors who are 45 or older are charged $0 for the ride** according to the current pricing logic. Confirm that this is the intended rule.
4. **The program does not show a ride-eligibility message when the height is 120 cm or less.** You may want to add an `else` message explaining that the visitor does not meet the height requirement.

## Future Improvements

- Support both feet and centimeters correctly.
- Validate the unit, age, height, and photo response.
- Display a clear message when the visitor is too short to ride.
- Ask the user to confirm the pricing rules for visitors aged 45 and above.
- Format the ticket result in a cleaner summary.

## License

This project is intended for learning and personal practice. Add a license if you plan to publish or distribute it.
