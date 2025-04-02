import React from 'react';
import { NavButton, NavItem, NavSeparator } from '@/components/layouts/Navigation/Nav';
import { appPages, authPages } from '@/config/pages.config';
import Icon from '@/components/icon/Icon';
import Badge from '@/components/ui/Badge';
import User from '@/components/layouts/User/User';
import usersDb, { TUser } from '@/mocks/db/users.db';
import { signOut, useSession } from 'next-auth/react';

const UserTemplate = () => {
	const { data: session } = useSession();
	const userData: TUser = usersDb.find((key) => key.username === session?.user?.name) as TUser;

	return (
		<User
			isLoading={false}
			name={userData?.firstName}
			nameSuffix={userData?.isVerified && <Icon icon='HeroCheckBadge' color='blue' />}
			position={userData?.position}
			src={userData?.image?.thumb}
			suffix={
				<Badge color='amber' variant='solid' className='text-xs font-bold'>
					PRO
				</Badge>
			}>
			<NavSeparator />
			<NavItem {...authPages.profilePage} />
			<NavItem {...appPages.mailAppPages.subPages.inboxPages}>
				<Badge variant='solid' className='leading-none'>
					3
				</Badge>
				<NavButton icon='HeroPlusCircle' title='New Mail' onClick={() => {}} />
			</NavItem>
			<NavItem text='Logout' icon='HeroArrowRightOnRectangle' onClick={() => signOut()} />
		</User>
	);
};

export default UserTemplate;
