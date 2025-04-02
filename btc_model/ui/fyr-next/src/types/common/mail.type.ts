import { Descendant } from 'slate';
import { TUser } from '../../mocks/db/users.db';

export type TMail = {
	id: number;
	user: TUser;
	fold: string;
	dateTime: string;
	isNew?: boolean;
	title: string;
	content: Descendant[];
	attachment?: string[];
	flag?: boolean;
};
