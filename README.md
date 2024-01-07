# Battle Master

Battle Master (btlmaster) is an AI agent created to play Pokemon battles (particularly by connecting to an instance of [Pokemon Shodown](https://pokemonshowdown.com/)). It uses the [CLARION cognitive architecture](https://sites.google.com/site/drronsun/clarion/clarion-project) as opposed to any particular AI paradigm.

In creator Ron Sun's words from the _Oxford Handbook of Cognitive Science_, CLARION is
> ... a hybrid cognitive architecture... that is signicantly dierent from most
existing cognitive architectures in several important respects. For one thing, the CLARION cognitive
architecture is hybrid in that it (a) combines connectionist and symbolic representations computationally,
(b) combines implicit and explicit psychological processes, and (c) combines cognition (in the narrow
sense) and other psychological processes (such as motivation and emotion).

## Usage

Battle master is intended to be an executable application. It is capable of connecting to a Pokemon Showdown server to play against opponents. Configuration (such as user credentials) and a running Pokemon Showdown server are all that is needed to run Battle Master.

### Clone the project and install dependencies
Clone the project and create a virtual environment.
```bash
git clone git@github.com:SirSkaro/battle-master.git
cd battle-master
python -m venv .venv
source .venv/bin/activate   #.venv\Scripts\activate.bat for Windows
pip install -r requirements.txt
```
The rest of the documentation assumes your working directory is the root of the project.

### Configure
Rename `config.ini.template` to `config.ini`.

#### Agent user configuration
Battle Master will log into a Pokemon Shdown server as a registered user. As such, you will need to have an account registered. Specify this account's credentials in the `showdown:username` and `showdown:password` fields.

Additionally, specify the name of the user you want the agent to challenge upon startup in the `opponent:username` field.

#### Showdown configuration
Provide the location of the Pokemon Showdown server and the authentication server in the `showdown:server_url` and `showdown:auth_url` fields, respectively. It is recommended to use Smogon's authentication server to easily go back and forth between Pokemon Showdown servers.

Your config file should look something like this:
```ini
[showdown]
username=Foo
password=Bar
server_url=sim.smogon.com:8000   # or localhost:8000 if running locally
auth_url=https://play.pokemonshowdown.com/action.php?

[opponent]
username=Probably your alt
```
### Running the Agent
```python
python -m battlemaster
```

## Development/Local Setup
If you want a completely local setup (such as for development purposes), you can run a Pokemon Showdown server locally. You can also disable security to remove rate limiting and throttling, which can be useful for benchmarking. 

### Docker
Included in the top-level `local-setup` directory is a Dockerfile to create an image of a Pokemon Showdown with security disabled (including automated chat moderation daemons). It runs on the default port 8000.
```bash
docker build -t pokemon-showdown -f local-setup/PokemonShowdownDockerfile .
docker run -p 8000:8000 -d pokemon-showdown:latest
```

Alternatively you can pull the source code for Pokemon Showdown and manually run it. This will require an installation of Node.js.
```bash
git clone https://github.com/smogon/pokemon-showdown.git
cd pokemon-showdown
npm install
cp config/config-example.js config/config.js
node pokemon-showdown start --no-security
```

Pokemon Showdown will be available at `http://localhost:8000`. 

## Contributing

This project is currently for scholastic credit. As such, not contributions will be accepted until after the class finishes (May 2024).

## License

[MIT](https://choosealicense.com/licenses/mit/)
