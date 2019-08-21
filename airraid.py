from math import atan2, cos, sin
from random import choice, randint, uniform
from time import sleep, time
from typing import Set
import os
import pygame


def fire_artillery():
	objects.add(Shell(random_bottom_pixel(), fuzz_position(pygame.mouse.get_pos()), shell_damage, shell_speed))


def fuzz_position(pos: (int, int), amt: int = 10) -> (int, int):
	x, y = pos
	x += randint(-amt, amt)
	y += randint(-amt, amt)
	return x, y


def game_text(text: str, coords: (int, int) = (0, 0), size: int = 12):
	myfont = pygame.font.SysFont('Consolas', size)
	textsurface = myfont.render(text, True, (0, 0, 0))
	screen.blit(textsurface, coords)


def get_files_with_extension(location: str, extension: str) -> Set[str]:
	extension = '.' + extension
	filenames = set()
	for file in os.listdir(location):
		if file.endswith(extension):
			filenames.add(location+'/'+file)
	return filenames


def leave():
	pygame.display.quit()
	pygame.quit()
	exit()


def random_airship_image() -> pygame.Surface:
	airship_image_filenames = get_files_with_extension('img/airship', 'png')
	filename = choice(list(airship_image_filenames))
	return pygame.image.load(filename)


def random_bottom_pixel() -> (int, int):
	x = randint(0, screen.get_width())
	y = screen.get_height()
	return x, y


def random_left_pixel() -> (int, int):
	x = randint(-200, -100)
	y = randint(0, screen.get_height()-100)
	return x, y


def sfx(category: str):
	filename = choice(list(get_files_with_extension('sfx/'+category, 'wav')))
	try:
		pygame.mixer.find_channel().queue(pygame.mixer.Sound(filename))
	except AttributeError:
		pass


class Shell:
	def __init__(self, source: (int, int), destination: (int, int), speed: int, base_damage: int):
		self.position = source
		self.destination = destination
		self.speed = speed
		self.base_damage = base_damage

	# properties
	@property
	def damage(self) -> int:
		return round(uniform(.5, 1.5) * self.base_damage)

	@property
	def delta(self) -> (int, int):
		return tuple(self.position[i] - self.destination[i] for i in range(2))

	@property
	def dist(self) -> float:
		dx, dy = self.delta
		return (dx**2 + dy**2)**.5

	@property
	def onscreen(self) -> bool:
		x, y = self.position
		sx, sy = screen.get_size()
		return 0 <= x <= sx and 0 <= y <= sy

	@property
	def theta(self) -> float:
		dx, dy = self.delta
		return atan2(dy, dx)

	@property
	def vxy(self) -> (float, float):
		theta = self.theta
		return -self.speed*cos(theta), -self.speed*sin(theta)

	# methods
	def detonate(self):
		for airship in {i for i in objects if isinstance(i, Airship)}:
			if airship.includes(self.position):
				airship.hit(self.damage)
		objects.remove(self)
		objects.add(Burst(self.position))
		sfx('burst')
		del self

	def pos_in(self, ticks: int) -> (int, int):
		"""Get position of shell in n ticks"""
		x, y = self.position
		vx, vy = self.vxy
		x += round(ticks*vx)
		y += round(ticks*vy)
		return x, y

	def render(self):
		pygame.draw.aaline(screen, black, self.pos_in(-1), self.position)

	def tick(self):
		if self.dist < self.speed:
			return self.detonate()
		self.position = self.pos_in(1)
		# check if offscreen
		if not self.onscreen:
			objects.remove(self)
			del self


class Airship:
	def __init__(self, image: pygame.Surface, source: (int, int)):
		self.image = image
		self.position = source
		self.health = self.max_health

	# properties
	@property
	def area(self) -> int:
		x, y = self.image.get_size()
		return x*y

	@property
	def damage(self) -> int:
		return self.area // 50

	@property
	def max_health(self) -> int:
		return self.area // 100

	@property
	def speed(self) -> float:
		return 5000 / self.area * max(.5, self.health / self.max_health)

	# methods
	def hit(self, damage: int):
		global score
		self.health -= damage
		if self.health <= 0:
			objects.remove(self)
			score += self.max_health
			del self

	def includes(self, coords: (int, int)) -> bool:
		x, y = coords
		xmin, ymin = self.position
		xmax, ymax = xmin+self.image.get_width(), ymin+self.image.get_height()
		return xmin <= x <= xmax and y <= ymax

	def render(self):
		screen.blit(self.image, self.position)
		# todo HP
		x, y = self.position
		y += self.image.get_height()
		game_text('HP: {}/{}'.format(self.health, self.max_health), (x, y))

	def tick(self):
		x, y = self.position
		x += self.speed
		self.position = x, y
		# todo check if over structure
		if screen.get_width() < self.position[0]:
			objects.remove(self)
			del self


class Burst:
	def __init__(self, position: (int, int)):
		self.position = position
		self.radius = 0
		self.radius_velocity = 5
		self.t = 0

	def render(self):
		# goal: white -> yellow -> orange -> red
		color = 255, 255 - 255//11 * self.t, max(0, 255 - 255//5 * self.t)
		pygame.draw.circle(screen, color, self.position, self.radius)

	def tick(self):
		self.radius += self.radius_velocity
		self.radius_velocity -= 1
		self.t += 1
		if self.radius < 0:
			objects.remove(self)
			del self


# do not touch these variables after game start
black = (0,)*3
white = (255,)*3
refresh = pygame.display.flip
target_fps = 30

artillery_timeout = .3
shell_damage = 10
shell_speed = 10
# touch these idgaf
pygame.init()
pygame.mixer.init()
pygame.mixer.music.load('sfx/airraid.wav')
pygame.mixer.music.play(-1)
pygame.mixer.set_num_channels(16)
screen = pygame.display.set_mode((1000, 500), pygame.RESIZABLE) # type: pygame.Surface

current_timeout = 0
objects = set() # type: set
paused = False
score = 0

while 1: # main loop
	start_time = time()
	# render
	screen.fill((0, 128, 255))
	for obj in objects:
		obj.render()
	game_text(str(score), (0, 0), 20)
	refresh()
	# check for keypresses
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			leave()
		elif event.type == pygame.KEYDOWN:
			if event.key == pygame.K_ESCAPE:
				leave()
			elif event.key == pygame.K_p:
				paused = not paused
		elif event.type == pygame.VIDEORESIZE:
			pygame.display.set_mode(event.size, pygame.RESIZABLE)
	# fire!
	if pygame.mouse.get_pressed()[0] and not current_timeout:
		fire_artillery()
		current_timeout = artillery_timeout
	# only do next ones if unpaused
	if paused:
		continue
	# simulate existing objects
	for obj in {i for i in objects}:
		obj.tick()
	# spawn new airships at random left side
	if len([i for i in objects if isinstance(i, Airship)]) < 4:
		objects.add(Airship(random_airship_image(), random_left_pixel()))
	# todo airships damage you at right side
	remaining_time = 1/target_fps - (time() - start_time)
	if 0 < remaining_time:
		sleep(remaining_time)
	# fire timeout
	if current_timeout:
		if 1/target_fps < current_timeout:
			current_timeout -= 1/target_fps
		else:
			current_timeout = 0
