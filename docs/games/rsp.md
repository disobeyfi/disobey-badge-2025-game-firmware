# Rock Scissors Paper

Our version: https://bigbangtheory.fandom.com/wiki/Rock,_Paper,_Scissors,_Lizard,_Spock

Best of three.

## Messages

### `RPSStart`

#### Parameters

| Name    | Description         |
| ------- | ------------------- |
| `round` | Number of the round |

### `RPSMove`

When player has selected their option and waiting time is over, both badges sends this message to each other.

#### Parameters

| Name   | Description                                                                        |
| ------ | ---------------------------------------------------------------------------------- |
| `move` | Selected option from the five (rock, scissors, paper, spock or lizzard) as integer |

### `RPSEnd`

Sent when either of players win and game ends.

#### Parameters

| Name         | Description                                                                        |
| ------------ | ---------------------------------------------------------------------------------- |
| `move`       | Selected option from the five (rock, scissors, paper, spock or lizzard) as integer |
| `iam_winner` | Is current user the winner or opponent                                             |
